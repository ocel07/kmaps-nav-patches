"""IDAPython (IDA 9, ARM64): fix-rate candidates of a native navigation engine + our byte-patch sites as ledger rows.

Run inside IDA (or through the IDA MCP execute_python) on the ORIGINAL library database (not the patched .so):
    exec(open(r'<this file>').read()); main(r'<out.tsv>', 'navsdk', r'<tools/tmap/navsdk_<ver>.json>')
    exec(open(r'<this file>').read()); main(r'<out.tsv>', 'engine')
Output feeds ledger.py like scan_smali.py output (kind class desc detail n + info columns).

Reach set: functions called (BL / tail B, depth <= MAX_DEPTH) from the per-fix entry points of the target (TARGETS).
Virtual calls (BLR) are not followed: methods reached only through a vtable are listed as extra roots.
Kinds:
  COUNTER  LDR w,[m] ; ADD/SUB/CINC/CSINC w',w,#k ; STR w',[m]  along the code path (unconditional B followed,
           conditional branches fall through). desc = member offset '+0x3e0' or global symbol ('global' if unnamed),
           detail = '+1' / '-5' / '+r' (register addend) / 'inc' (CSINC/CINC, capped increment)
  CTRCMP   that counter value (or a later read of the same class member / global in the reach set) compared with an
           immediate >= 2. detail = 'cmp #4'
  ONE_SEC  integer 1000 (MOV/CMP/ADD/SUB #0x3e8) whose register feeds MUL/DIV/CMP/a call argument within a few
           instructions, or a float/double literal 1000.0 / 0.001 / 3.6 / 1/3.6 / 3600.0 used by FMUL/FDIV
           (ms <-> s, km/h <-> m per 1 s). detail = 'int1000 mul' / 'f3.6 fdiv' ...
  PATCH    navsdk only: one row per entry of the patch JSON (tools/tmap/navsdk_<ver>.json), class = function that
           contains the patched address (ELF header entries: 'ELF'), desc = entry id (W, N2-1, CAVE, SLOT ...),
           detail = original first instruction with branch targets replaced by 'L'
Key columns (kind, class = '<lib>:<demangled function>' (argument list only for overloaded names), desc, detail, n)
contain no addresses; the address, call depth and disassembly are info columns (they change with every build).
"""
import json, re, struct
import idautils, idc, ida_bytes, ida_funcs, ida_nalt, ida_segment

MAX_DEPTH = 6
TARGETS = {
    'navsdk': dict(lib='NavigationSDK', roots=[
        'nativeInputLocationData', 'CNaviController::InputLocationData', 'CNaviModule::API_InputLocation',
        'CNaviModule::ReceiveGps', 'CNaviModule::MapMatch',
        'CNaviController::GetRouteGuidance', 'CNaviModule::API_GetRouteGuidance', 'CRGServiceManager::GetDriveInfo',
        # reached through vtables from NcMapMatch::Matching / CRGPlayer
        'NcRouteMatchEX::SetGpsParsedData', 'NcRouteMatchEX::MapMatching', 'NcLocalMatch::SetGpsParsedData',
        'NcLocalMatch::ICalcMapMatching', 'NcBaseMatch::AddGpaData', 'CRGPlayer::GetDriveInfo',
        'SectionSpeedMonitor::Update', 'SpeedCalculator::Update']),
    'engine': dict(lib='tmapnavigationengine', roots=[
        'Java_com_tmapmobility_tmap_tmapnavigationengine_TmapNavigationEngine_putLocation',
        'MapMatch::PutLocation', 'MapMatch::GetMapMatchResult', 'RouteGuidanceResult::GetDriveInfo',
        'RouteGuidanceVoice::MakeVoiceService', 'RouteGuidanceVoice::SDIService', 'DangerAreaInfomation::GetDAInfo']),
}
SKIP = ('.', 'std::', 'operator', '__', 'mem', 'str', 'sqlite', 'png', 'zlib', 'inflate', 'deflate', 'je_', 'Json::',
        'google::protobuf', 'flatbuffers', 'SDL_', 'pthread', 'vsm_log', 'nanopb', 'pb_')
FCONST = {1000.0: 'f1000', 0.001: 'f0.001', 3.6: 'f3.6', 1 / 3.6: 'f1/3.6', 3600.0: 'f3600', 0.2777777777777778: 'f1/3.6'}
GLOBAL_AUTO = re.compile(r'^(dword|qword|word|byte|unk|off|xmmword|stru|flt|dbl)_[0-9A-F]+$')


def short(n):
    d = idc.demangle_name(n, idc.get_inf_attr(idc.INF_SHORT_DN))
    return d or n


def regno(op):
    m = re.match(r'^[WX](\d+|ZR)$', op)
    return m.group(1) if m else None


def imm(op):
    m = re.match(r'^#(-?0x[0-9A-Fa-f]+|-?\d+)$', op.split(';')[0].strip())
    return int(m.group(1), 0) if m else None


class Names:
    def __init__(self, lib):
        self.lib = lib
        self.parent = {}
        cnt = {}
        for f in idautils.Functions():
            b = short(idc.get_func_name(f)).split('(')[0]
            cnt[b] = cnt.get(b, 0) + 1
        self.over = {b for b, c in cnt.items() if c > 1}

    def base(self, f):
        return short(idc.get_func_name(f)).split('(')[0]

    def key(self, f):
        return f'{self.lib}:' + self.name(f)

    def name(self, f, hops=0):
        s = short(idc.get_func_name(f))
        if re.match(r'^(sub|nullsub|j_sub)_[0-9A-F]+$', s):     # unnamed helper: 'sub<caller>' (address-free)
            p = self.parent.get(f)
            return f'sub<{self.name(p, hops + 1)}>' if p is not None and hops < 8 else 'sub'
        b = s.split('(')[0]
        return s if b in self.over else b


def callees(f):
    out, fn = set(), ida_funcs.get_func(f)
    for ea in idautils.FuncItems(f):
        m = idc.print_insn_mnem(ea)
        if m in ('BL', 'B'):
            g = ida_funcs.get_func(idc.get_operand_value(ea, 0))
            if g is None:
                continue
            t = g.start_ea
            n = idc.get_func_name(t)
            if n.startswith('.'):      # exported functions are called through their PLT thunk ('._ZN...')
                r = idc.get_name_ea_simple(n[1:])
                if r != idc.BADADDR and ida_funcs.get_func(r):
                    t = ida_funcs.get_func(r).start_ea
            if t != fn.start_ea:
                out.add(t)
    return out


def reach(names, roots):
    by = {}
    for f in idautils.Functions():
        by.setdefault(names.base(f), []).append(f)
    depth = {f: 0 for r in roots for f in by.get(r, [])}
    missing = [r for r in roots if r not in by]
    todo = list(depth.items())
    while todo:
        f, d = todo.pop()
        if d >= MAX_DEPTH or names.base(f).startswith(SKIP):     # library internals are not descended into
            continue
        for c in callees(f):
            if c not in depth or depth[c] > d + 1 or depth[c] == d + 1 and c in names.parent and \
                    short(idc.get_func_name(names.parent[c])) > short(idc.get_func_name(f)):
                depth[c] = d + 1
                names.parent[c] = f
                todo.append((c, d + 1))
    return {f: d for f, d in depth.items() if not names.base(f).startswith(SKIP)}, missing


def mem_key(op):
    """'[X19,#0x3E0]' -> '+0x3e0'; '[X8,#dword_1E17A4@PAGEOFF]' -> 'global'/symbol; stack and indexed -> None"""
    m = re.match(r'^\[X(\d+)(?:,#(0x[0-9A-Fa-f]+|\d+))?\]$', op)
    if m:
        return f'+0x{int(m.group(2) or "0", 0):x}'
    m = re.match(r'^\[X\d+,#(\w+)@PAGEOFF\]$', op)
    if m:
        s = m.group(1)
        return 'global' if GLOBAL_AUTO.match(s) else 'g:' + short(s)
    return None


def path(f, ea, n):
    """the next n instructions after ea along the code path: unconditional B inside the function is followed,
    conditional branches fall through; stops at RET, at calls (BL/BLR clobber) and at the function end"""
    def same(x):
        g = ida_funcs.get_func(x)
        return g is not None and g.start_ea == f

    out, cur = [], ea
    for _ in range(n):
        m = idc.print_insn_mnem(cur)
        if m == 'B':
            cur = idc.get_operand_value(cur, 0)
        else:
            cur = idc.next_head(cur, idc.BADADDR)
        if cur == idc.BADADDR or not same(cur):
            break
        out.append(cur)
        if idc.print_insn_mnem(cur) in ('RET', 'BR', 'BLR', 'BL'):
            break
    return out


WRITES0 = ('ADD', 'SUB', 'MOV', 'LDR', 'LDRB', 'LDRH', 'LDRSW', 'CSINC', 'CINC', 'CSEL', 'MUL', 'MADD', 'MSUB',
           'SDIV', 'UDIV', 'LSL', 'LSR', 'ASR', 'AND', 'ORR', 'EOR', 'NEG', 'SXTW', 'UBFX', 'SBFX', 'CSET', 'CSNEG',
           'MOVK', 'MOVZ', 'FCVTZS', 'FCVTZU', 'FCVTAS', 'ADDS', 'SUBS', 'BIC', 'UXTB', 'UXTH', 'SXTB', 'SXTH')


def track(f, ea, reg, n=14):
    """follow the value loaded into reg at ea: yields ('store', mem_op, delta, at), ('cmp', imm, delta, at)"""
    val = {reg: 0}            # register number -> delta from the loaded value (None = '+r')
    for a in path(f, ea, n):
        m = idc.print_insn_mnem(a)
        o = [idc.print_operand(a, i) for i in range(4)]
        r0, r1, r2 = regno(o[0]), regno(o[1]), regno(o[2])
        if m in ('CMP', 'CMN', 'SUBS') and (r0 if m != 'SUBS' else r1) in val:
            src = r0 if m != 'SUBS' else r1
            c = imm(o[1] if m != 'SUBS' else o[2])
            if c is not None:
                yield ('cmp', -c if m == 'CMN' else c, val[src], a)
            if m != 'SUBS':
                continue
        if m.startswith('STR') and r0 in val and val[r0] != 0:
            yield ('store', o[1], val[r0], a)
            continue
        if m.startswith(('STR', 'STP', 'CMP', 'CMN', 'TST', 'FCMP', 'TBZ', 'TBNZ', 'CBZ', 'CBNZ', 'B.')) or m == 'B':
            continue
        new = None
        if m in ('ADD', 'SUB') and r1 in val and isinstance(val[r1], int):
            k = imm(o[2])
            if k is not None and 1 <= k <= 16:
                new = val[r1] + (k if m == 'ADD' else -k)
            elif r2 is not None and o[3] == '':
                new = 'r'
        elif m == 'ADD' and r2 in val and r1 is not None and r1 not in val:
            new = 'r'
        elif m in ('CINC',) and r1 in val:
            new = 'inc'
        elif m == 'CSINC' and (r2 in val or r1 in val):
            new = 'inc'
        elif m == 'MOV' and r1 in val:
            new = val[r1]
        if r0 is not None and m in WRITES0 or m.startswith(('LDR', 'FMOV', 'FCVT')) and r0 is not None:
            val.pop(r0, None)
        if new is not None and r0 is not None:
            val[r0] = new
        if not val:
            return


def fconst(ea):
    """value of a float/double literal loaded by LDR Sn/Dn from a data address"""
    o = idc.print_operand(ea, 0)
    if not re.match(r'^[SD]\d+$', o):
        return None
    t = next(iter(idautils.DataRefsFrom(ea)), None)      # ADRP+LDR [Xn,#qword_x@PAGEOFF]: the full address is the xref
    if t is None or ida_segment.getseg(t) is None:
        return None
    b =ida_bytes.get_bytes(t, 8 if o[0] == 'D' else 4)
    if not b:
        return None
    v = struct.unpack('<d' if o[0] == 'D' else '<f', b)[0]
    for c, name in FCONST.items():
        if c and abs(v - c) <= abs(c) * 1e-6:
            return name
    return None


def scan(names, funcs, emit):
    counters = set()
    for f, d in sorted(funcs.items()):
        fk = names.key(f)
        for ea in idautils.FuncItems(f):
            m = idc.print_insn_mnem(ea)
            if m in ('LDR', 'LDRB', 'LDRH', 'LDRSW'):
                r = regno(idc.print_operand(ea, 0))
                mk = mem_key(idc.print_operand(ea, 1))
                fc = fconst(ea) if r is None else None
                if fc:
                    for a in path(f, ea, 6):
                        if idc.print_insn_mnem(a) in ('FMUL', 'FDIV', 'FNMUL', 'FMADD', 'FMSUB') and \
                                idc.print_operand(ea, 0) in [idc.print_operand(a, i) for i in (1, 2, 3)]:
                            emit('ONE_SEC', fk, fc, idc.print_insn_mnem(a).lower(), a, d, idc.GetDisasm(a))
                            break
                    continue
                if r is None or mk is None:
                    continue
                op = idc.print_operand(ea, 1)
                for ev, x, delta, at in track(f, ea, r):
                    if ev == 'store' and x == op and delta not in (0, None):
                        det = delta if isinstance(delta, str) else f'{delta:+d}'
                        det = '+r' if det == 'r' else det
                        emit('COUNTER', fk, mk, det, at, d, m + ' ' + idc.GetDisasm(at))
                        counters.add((names.base(f).rsplit('::', 1)[0], mk))
                        for ev2, c, _, at2 in track(f, ea, r, 18):
                            if ev2 == 'cmp' and c >= 2:
                                emit('CTRCMP', fk, mk, f'cmp #{c}', at2, d, 'counter')
                        break
            elif m in ('MOV', 'CMP', 'ADD', 'SUB', 'MOVZ') and imm(idc.print_operand(ea, 1 if m in ('MOV', 'CMP', 'MOVZ') else 2)) == 1000:
                if m == 'CMP':
                    emit('ONE_SEC', fk, 'int1000', 'cmp', ea, d, idc.GetDisasm(ea))
                    continue
                r = regno(idc.print_operand(ea, 0))
                use = None
                for a in path(f, ea, 6):
                    mm = idc.print_insn_mnem(a)
                    ops = [regno(idc.print_operand(a, i)) for i in range(4)]
                    if mm in ('MUL', 'MADD', 'MSUB', 'SDIV', 'UDIV', 'SMULL', 'UMULL', 'SMADDL') and r in ops[1:]:
                        use = mm.lower(); break
                    if mm in ('CMP', 'CMN') and r in ops[:2]:
                        use = 'cmp'; break
                    if mm in ('BL', 'BLR') and r is not None and r.isdigit() and int(r) <= 7:
                        use = 'arg'; break
                    if mm.startswith('STR') and ops[0] == r:
                        use = 'store'; break
                    if ops[0] == r and not mm.startswith(('STR', 'CMP', 'B')):
                        break
                if use:
                    emit('ONE_SEC', fk, 'int1000', use, ea, d, idc.GetDisasm(ea))
    return counters


def threshold_reads(names, funcs, counters, emit):
    """a counter member (class, offset) / global read anywhere in the reach set and compared with an immediate >= 2"""
    for f, d in sorted(funcs.items()):
        cls = names.base(f).rsplit('::', 1)[0]
        for ea in idautils.FuncItems(f):
            if not idc.print_insn_mnem(ea).startswith('LDR'):
                continue
            mk = mem_key(idc.print_operand(ea, 1))
            r = regno(idc.print_operand(ea, 0))
            if mk in (None, '+0x0') or r is None or ((cls, mk) not in counters and not (mk.startswith(('g:', 'global')) and
                                                                            any(k == mk for _, k in counters))):
                continue
            for ev, c, delta, at in track(f, ea, r, 6):
                if ev == 'cmp' and c >= 2:
                    emit('CTRCMP', names.key(f), mk, f'cmp #{c}', at, d, 'member read')
                if ev == 'store':
                    break


def norm_ins(ea):
    ins = re.sub(r'\s+', ' ', idc.GetDisasm(ea).split(';')[0]).strip()
    return re.sub(r'\b(loc|sub|locret|off|unk|dword|qword|byte|word)_[0-9A-F]+\b|_Z\w+', 'L', ins)


def patch_rows(names, js, emit):
    p = json.load(open(js, encoding='utf-8'))
    for e in p['patches']:
        off = e['offset']
        ea = off    # RX segment: file offset == VA (checked in docs/tmap/N2_patch.md); RW headers are not code
        f = ida_funcs.get_func(ea)
        if e['id'] == 'SLOT' or f is None:
            fk, ins = f'{names.lib}:ELF', e['desc'].split(' ')[0]
        else:
            fk, ins = names.key(f.start_ea), norm_ins(ea)
            if ida_bytes.get_bytes(ea, 4).hex() != e['orig'][:8]:
                ins = '?orig-mismatch ' + ins
        emit('PATCH', fk, e['id'], ins, ea, '', e['desc'][:100], e['id'])


def main(out, target, patches=None):
    t = TARGETS[target]
    names = Names(t['lib'])
    funcs, missing = reach(names, t['roots'])
    rows, seen, at = [], {}, set()

    def emit(kind, fn, desc, detail, ea, depth, info, pid=''):
        if (kind, ea, desc, detail) in at:
            return
        at.add((kind, ea, desc, detail))
        k = (kind, fn, desc, detail)
        seen[k] = seen.get(k, 0) + 1
        rows.append((kind, fn, desc, detail, str(seen[k]), hex(ea), str(depth), re.sub(r'\s+', ' ', info), pid))

    counters = scan(names, funcs, emit)
    threshold_reads(names, funcs, counters, emit)
    if patches:
        patch_rows(names, patches, emit)
    with open(out, 'w', encoding='utf-8', newline='\n') as o:
        o.write('kind\tclass\tdesc\tdetail\tn\taddr\tdepth\tinfo\tpatch_id\n')
        for r in rows:
            o.write('\t'.join(r) + '\n')
    from collections import Counter
    return (f'{ida_nalt.get_root_filename()}: {len(funcs)} reachable functions, {len(rows)} rows '
            f'{dict(Counter(r[0] for r in rows))}, missing roots {missing}')

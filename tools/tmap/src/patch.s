// libNavigationSDK.so (TMAP 11.8.4.4075) time-weighted fix-rate patch.
// Linked at .text = 0xf0000 so that every label sits at its real file offset (== VA in the RX segment).
    // extern SLOT = 0x1e8050 (--defsym)
    .equ S_NOW,     0x00            // int64  last fix time (CNaviModule+0x2A8, ms)
    .equ S_W,       0x08            // int32  w = clamp(dt,1..1000) ms
    .equ S_SMACC,   0x0C            // int32  tunnel-speed smoothing 1 Hz accumulator
    .equ S_ODOT,    0x10            // double odometer fraction (total, +0x7CC)
    .equ S_ODOR,    0x18            // double odometer fraction (on-route, +0x7D0)
    .equ S_SAVE,    0x30            // int64  last SavePersistentState time
    .equ S_LOG1,    0x38            // int64  last SpeedCalculator "Update(initial/shaded)" log
    .equ S_LOG2,    0x40            // int64  last SpeedCalculator "Update:" log
    .equ S_TRKT,    0x48            // int32  ms accumulated since last route-track write
    .equ S_TRKTRY,  0x50            // int64  last route-track write attempt
    // extern PLT_RTENV_GETINSTANCE = 0x1ba890 (--defsym)
    // extern PLT_SAVEPERSIST = 0x1bd450 (--defsym)
    // extern PLT_LOG = 0x1bd5b0 (--defsym)
    .equ CAVE,                  0x15956c   // CRGServiceConfig::FileWriteDefaultConfig (no callers)
    // extern T_f7f2c = 0xf7f2c (--defsym)
    // extern T_f7f34 = 0xf7f34 (--defsym)
    // extern T_f8d60 = 0xf8d60 (--defsym)
    // extern T_109678 = 0x109678 (--defsym)
    // extern T_10e430 = 0x10e430 (--defsym)
    // extern T_10f86c = 0x10f86c (--defsym)
    // extern T_10f898 = 0x10f898 (--defsym)
    // extern T_10fb98 = 0x10fb98 (--defsym)
    // extern T_10fb9c = 0x10fb9c (--defsym)
    // extern T_10fba4 = 0x10fba4 (--defsym)
    // extern T_133ff8 = 0x133ff8 (--defsym)
    // extern T_134088 = 0x134088 (--defsym)

    .equ BASE, 0xf0000
    .text
    .globl _start
_start:

// ---------------- in-place patch sites (ascending) ----------------
    .org 0xf7c74 - BASE
b_f7c74:  bl   cave_w                    // CNaviModule::MapMatch: was BL CRuntimeEnv::GetInstance
e_f7c74:
    .org 0xf7f10 - BASE
b_f7f10:  b    cave_trk                  // was LDR W8,[X19,#0x3F0] (route-track counter)
e_f7f10:
    .org 0xf7fec - BASE
b_f7fec:  b    cave_flush                // was CMP W1,#1 (flush when RG service ends)
e_f7fec:
    .org 0xf8c38 - BASE
b_f8c38:  bl   cave_wrinit               // was ADD W9,W25,#2
          nop                            // was SUB W10,W11,W25
e_f8c38:
    .org 0xf8c48 - BASE
b_f8c48:  sub  w9, w9, w28               // was SUB W9,W9,#3
e_f8c48:
    .org 0xf8cf4 - BASE
b_f8cf4:  cmp  w9, w25                   // was CMP W9,#2
          add  w10, w10, w28             // was ADD W10,W10,#3
e_f8cf4:
    .org 0xf8d5c - BASE
b_f8d5c:  b    cave_wrreset              // was STR WZR,[X20,#0x3E0]
e_f8d5c:
    .org 0x109674 - BASE
b_109674: b    cave_smooth               // was ADD W8,W8,W23
e_109674:
    .org 0x10967c - BASE
b_10967c: nop                            // was LSR W8,W8,#1 (moved into cave_smooth)
e_10967c:
    .org 0x10976c - BASE
b_10976c: bl   stub_w3                   // was MOV W3,#1000
e_10976c:
    .org 0x109b98 - BASE
b_109b98: bl   stub_ramp                 // was CMP W9,#0xA
          nop                            // was MOV W10,#0xA
e_109b98:
    .org 0x109dd0 - BASE
b_109dd0: bl   stub_secs                 // was LSR X8,X8,#0x26 (ms/1000)
e_109dd0:
    .org 0x10e400 - BASE
b_10e400: b    cave_odo                  // was FCVTZS W8,D0
e_10e400:
    .org 0x10f7b8 - BASE
b_10f7b8: b    cave_hwinc                // was CMP W8,#0x12C
e_10f7b8:
    .org 0x10f7f0 - BASE
b_10f7f0: b    cave_off1                 // was ADD W8,W8,#1
e_10f7f0:
    .org 0x10f868 - BASE
b_10f868: b    cave_off2                 // was ADD W8,W8,#2
e_10f868:
    .org 0x10f878 - BASE
b_10f878: cmp  w8, #4000                 // was CMP W8,#4
e_10f878:
    .org 0x10f880 - BASE
b_10f880: cmp  w8, #3999                 // was CMP W8,#3
e_10f880:
    .org 0x10fb74 - BASE
b_10fb74: b    cave_shade                // was FCVTZS W8,D0
e_10fb74:
    .org 0x110994 - BASE
b_110994: b    cave_hde                  // CheckHighwayDrivingException entry
e_110994:
    .org 0x1336dc - BASE
b_1336dc: bl   stub_sdib                 // was ADD W11,W9,#1
          cmp  w9, #1000                 // was CMP W9,#1
e_1336dc:
    .org 0x133fdc - BASE
b_133fdc: bl   stub_sdia                 // LDR W9,[X20,#0x320]; W10 = W9 + w
          cmp  w8, w27
          str  w10, [x20, #0x320]
          b.ge T_133ff8
          cmp  w9, #2000                 // was CMP W9,#2
          b.lt T_134088
          nop
e_133fdc:
    .org 0x139448 - BASE
b_139448: bl   cave_save                 // was BL SectionSpeedMonitor::SavePersistentState
e_139448:
    .org 0x1427e4 - BASE
b_1427e4: bl   cave_log1                 // was BL __android_log_print (Update(initial/shaded))
e_1427e4:
    .org 0x142850 - BASE
b_142850: bl   cave_log2                 // was BL __android_log_print (Update: totalDist=...)
e_142850:

// ---------------- code cave ----------------
    .org CAVE - BASE
b_cave:

// MapMatch hook: w = clamp(t - t_prev, 1..1000); backwards/first -> 1000; equal -> 1.
cave_w:
    ldr   x9, [x0, #0x2a8]
    adrp  x10, SLOT
    add   x10, x10, :lo12:SLOT
    ldr   x11, [x10, #S_NOW]
    str   x9, [x10, #S_NOW]
    sub   x9, x9, x11
    mov   x11, #1000
    cmp   x9, x11
    csel  x9, x9, x11, ls
    cmp   x9, #0
    csinc x9, x9, xzr, ne
    str   w9, [x10, #S_W]
    b     PLT_RTENV_GETINSTANCE

// N2-1: virtual GPS step = w
stub_w3:
    adrp  x16, SLOT
    add   x16, x16, :lo12:SLOT
    ldr   w3, [x16, #S_W]
    ret

// N2-1: speed ramp cap = max(1, w/100) km/h per fix (10 km/h per second)
stub_ramp:
    adrp  x16, SLOT
    add   x16, x16, :lo12:SLOT
    ldr   w10, [x16, #S_W]
    mov   w16, #100
    udiv  w10, w10, w16
    cmp   w10, #1
    csinc w10, w10, wzr, hs
    cmp   w9, w10
    ret

// N2-1: seconds field += new_ms/1000 - old_ms/1000 (X27 = new ms, W21 = step)
stub_secs:
    mov   x16, #1000
    sdiv  x17, x27, x16
    sub   x8, x27, w21, uxtw
    sdiv  x8, x8, x16
    sub   x8, x17, x8
    ret

// N2-1: tunnel speed hold (max+cur)/2 applied once per accumulated second
cave_smooth:
    adrp  x16, SLOT
    add   x16, x16, :lo12:SLOT
    ldr   w17, [x16, #S_W]
    ldr   w9, [x16, #S_SMACC]
    add   w9, w9, w17
    cmp   w9, #1000
    b.lt  1f
    sub   w9, w9, #1000
    add   w8, w8, w23
    lsr   w8, w8, #1
1:  str   w9, [x16, #S_SMACC]
    b     T_109678

// N2-5: odometer. total: rate gate d/(w/1000) >= 2 m/s, on-route: >= 1 m/s; fractional carry.
cave_odo:
    fcmp  d0, d0
    b.vs  9f
    adrp  x16, SLOT
    add   x16, x16, :lo12:SLOT
    ldr   w9, [x16, #S_W]
    ucvtf d1, w9
    mov   w10, #500
    ucvtf d2, w10
    fmul  d2, d0, d2
    fcmp  d2, d1
    b.lt  1f
    ldr   d3, [x16, #S_ODOT]
    fadd  d3, d3, d0
    fcvtms w8, d3
    scvtf d2, w8
    fsub  d3, d3, d2
    str   d3, [x16, #S_ODOT]
    ldr   w9, [x19, #0x7cc]
    add   w9, w9, w8
    str   w9, [x19, #0x7cc]
1:  ldr   w9, [x19, #0x170]
    cmp   w9, #2
    b.ne  9f
    mov   w10, #1000
    ucvtf d2, w10
    fmul  d2, d0, d2
    fcmp  d2, d1
    b.lt  9f
    ldr   d3, [x16, #S_ODOR]
    fadd  d3, d3, d0
    fcvtms w8, d3
    scvtf d2, w8
    fsub  d3, d3, d2
    str   d3, [x16, #S_ODOR]
    ldr   w9, [x19, #0x7d0]
    add   w9, w9, w8
    str   w9, [x19, #0x7d0]
9:  b     T_10e430

// N2-3: highway exception counter += w, cap 300000 ms
cave_hwinc:
    adrp  x16, SLOT
    add   x16, x16, :lo12:SLOT
    ldr   w9, [x16, #S_W]
    add   w8, w8, w9
    mov   w9, #0x93e0
    movk  w9, #0x4, lsl #16
    cmp   w8, w9
    csel  w8, w8, w9, lt
    str   w8, [x19, #0x988]
    b     T_10f898

// N2-2: off-route counter += w / += 2w
cave_off1:
    adrp  x16, SLOT
    add   x16, x16, :lo12:SLOT
    ldr   w16, [x16, #S_W]
    add   w8, w8, w16
    b     T_10f86c
cave_off2:
    adrp  x16, SLOT
    add   x16, x16, :lo12:SLOT
    ldr   w16, [x16, #S_W]
    add   w8, w8, w16, lsl #1
    b     T_10f86c

// N2-4: shadow-mode route confirm. count phase: d*100 < w (<10 m/s per-second distance);
//       hold phase (>=10000 ms): absolute d < 10 m from stale reference. count += w, confirm at >=10000 ms.
cave_shade:
    ldr   w8, [x19, #0x4d0]
    adrp  x16, SLOT
    add   x16, x16, :lo12:SLOT
    ldr   w9, [x16, #S_W]
    mov   w10, #10000
    cmp   w8, w10
    b.ge  2f
    fmov  d1, #10.0
    fmul  d2, d0, d1
    fmul  d2, d2, d1
    ucvtf d1, w9
    fcmp  d2, d1
    b.ge  8f
    b     3f
2:  fmov  d1, #10.0
    fcmp  d0, d1
    b.ge  8f
3:  add   w8, w8, w9
    str   w8, [x19, #0x4d0]
    cmp   w8, w10
    b.lt  T_10fb9c
    b     T_10fba4
8:  b     T_10fb98

// N2-3: NcRouteMatchEX::CheckHighwayDrivingException, ms version (31000 ms, -5w or -(35-speed)w)
cave_hde:
    ldr   w8, [x0, #0x2c8]
    orr   w8, w8, #2
    cmp   w8, #3
    b.ne  8f
    ldr   w8, [x0, #0x988]
    mov   w9, #31000
    cmp   w8, w9
    b.lt  8f
    adrp  x16, SLOT
    add   x16, x16, :lo12:SLOT
    ldr   w16, [x16, #S_W]
    ldr   s0, [x0, #0x524]
    mov   w9, #3
    str   w9, [x0, #0x170]
    fcmp  s0, #0.0
    b.ls  5f
    fmov  s1, #30.0
    fcmp  s0, s1
    b.gt  5f
    movz  w9, #0xc20c, lsl #16
    fmov  s1, w9
    fadd  s0, s0, s1
    ucvtf s1, w16
    fmul  s0, s0, s1
    scvtf s2, w8
    fadd  s0, s0, s2
    fcvtzs w8, s0
    b     6f
5:  add   w9, w16, w16, lsl #2
    sub   w8, w8, w9
6:  str   w8, [x0, #0x988]
    ret
8:  str   wzr, [x0, #0x988]
    ret

// N2-7a / N2-7b: SDI section debounce counters += w
stub_sdia:
    ldr   w9, [x20, #0x320]
    adrp  x16, SLOT
    add   x16, x16, :lo12:SLOT
    ldr   w16, [x16, #S_W]
    add   w10, w9, w16
    ret
stub_sdib:
    adrp  x16, SLOT
    add   x16, x16, :lo12:SLOT
    ldr   w16, [x16, #S_W]
    add   w11, w9, w16
    ret

// N2-9: SavePersistentState at most once per 1000 ms (X1 = time ms)
cave_save:
    adrp  x16, SLOT
    add   x16, x16, :lo12:SLOT
    ldr   x17, [x16, #S_SAVE]
    sub   x17, x1, x17
    cmp   x17, #900 
    b.lo  1f
    str   x1, [x16, #S_SAVE]
    b     PLT_SAVEPERSIST
1:  ret

// N2-9: per-call INFO logs at most once per 1000 ms of fix time
cave_log1:
    adrp  x16, SLOT
    add   x16, x16, :lo12:SLOT
    ldr   x17, [x16, #S_LOG1]
    ldr   x16, [x16, #S_NOW]
    sub   x17, x16, x17
    cmp   x17, #900 
    b.lo  1f
    adrp  x17, SLOT
    add   x17, x17, :lo12:SLOT
    str   x16, [x17, #S_LOG1]
    b     PLT_LOG
1:  mov   w0, #0
    ret
cave_log2:
    adrp  x16, SLOT
    add   x16, x16, :lo12:SLOT
    ldr   x17, [x16, #S_LOG2]
    ldr   x16, [x16, #S_NOW]
    sub   x17, x16, x17
    cmp   x17, #900 
    b.lo  1f
    adrp  x17, SLOT
    add   x17, x17, :lo12:SLOT
    str   x16, [x17, #S_LOG2]
    b     PLT_LOG
1:  mov   w0, #0
    ret

// N2-10: route-track write trigger. N = fixes since last write (cap 1200 < queue 1240),
//        T += w; write when T >= [this+0x3F0]*1000 (210 s) or N reaches 1200; attempts >= 1000 ms apart.
cave_trk:
    adrp  x16, SLOT
    add   x16, x16, :lo12:SLOT
    ldr   w9, [x16, #S_W]
    ldr   w10, [x16, #S_TRKT]
    add   w10, w10, w9
    str   w10, [x16, #S_TRKT]
    add   w1, w1, #1
    mov   w11, #1200
    cmp   w1, w11
    csel  w1, w1, w11, lt
    str   w1, [x19, #0x3e0]
    b.ge  1f
    ldr   w8, [x19, #0x3f0]
    mov   w11, #1000
    mul   w8, w8, w11
    cmp   w10, w8
    b.lt  9f
1:  ldr   x9, [x16, #S_NOW]
    ldr   x10, [x16, #S_TRKTRY]
    sub   x10, x9, x10
    cmp   x10, #900 
    b.lo  9f
    str   x9, [x16, #S_TRKTRY]
    b     T_f7f2c
9:  b     T_f7f34

cave_flush:
    cmp   w1, #1
    b.lt  9f
    adrp  x16, SLOT
    add   x16, x16, :lo12:SLOT
    ldr   x9, [x16, #S_NOW]
    ldr   x10, [x16, #S_TRKTRY]
    sub   x10, x9, x10
    cmp   x10, #900 
    b.lo  9f
    str   x9, [x16, #S_TRKTRY]
    b     T_f7f2c
9:  b     T_f7f34

// WriteRouteTrackFile loop setup: step s = max(1, ceil(N/B), round(3000*N/T)) entries (~3 s apart).
// in: W25 = N, X20 = this. out: W28 = s, W9 = N+s-1, W10 = 1-N, W25 = s-1 (loop bound).
cave_wrinit:
    adrp  x16, SLOT
    add   x16, x16, :lo12:SLOT
    ldr   w17, [x16, #S_TRKT]
    mov   w9, #3000
    mul   w9, w25, w9
    add   w9, w9, w17, lsr #1
    udiv  w9, w9, w17
    ldr   w10, [x20, #0x3f0]
    add   w17, w25, w10
    sub   w17, w17, #1
    udiv  w17, w17, w10
    cmp   w9, w17
    csel  w9, w9, w17, hi
    cmp   w9, #1
    csinc w28, w9, wzr, hs
    add   w9, w25, w28
    sub   w9, w9, #1
    mov   w10, #1
    sub   w10, w10, w25
    sub   w25, w28, #1
    ret

cave_wrreset:
    str   wzr, [x20, #0x3e0]
    adrp  x16, SLOT
    add   x16, x16, :lo12:SLOT
    str   wzr, [x16, #S_TRKT]
    b     T_f8d60
e_cave:

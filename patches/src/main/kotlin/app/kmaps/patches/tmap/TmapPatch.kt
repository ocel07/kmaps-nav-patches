package app.kmaps.patches.tmap

import app.kmaps.patches.shared.Constants.COMPATIBILITY_TMAP
import app.kmaps.patches.shared.Op
import app.kmaps.patches.shared.Site
import app.kmaps.patches.shared.applySites
import app.morphe.patcher.patch.PatchException
import app.morphe.patcher.patch.bytecodeContext
import app.morphe.patcher.patch.deleteResource
import app.morphe.patcher.patch.listApkEntries
import app.morphe.patcher.patch.patch
import app.morphe.patcher.patch.resourceFile

/*
 * TMAP: high-rate GNSS (docs/tmap-rate-patch.md, docs/tmap/J_java.md).
 * Java side: open the 1 Hz gates so every gps fix reaches the engine. The native engine (libNavigationSDK.so)
 * counts fixes as seconds and is patched separately to count elapsed milliseconds (docs/tmap/N2_patch.md).
 *  J1  GpsProvider.requestUpdate: gps requested every 1000 ms -> 100 ms
 *  J3  LocationReliabilityChecker.isIrregularTime: gps fixes with < 4 satellites (tunnel, u-blox dead reckoning)
 *      were held to 1 Hz -> every gps fix is exempt from the interval check
 *  J4  V2FilterConfig.ignoreTimeAfterLocationReceived: 900 ms window after an accepted fix -> 80 ms
 *  J5  V2FilterConfig.maxConsecutiveReject: 20 rejections (= 20 s at 1 Hz) -> scaled to the gps rate
 *  J7  LocationPrioritySelector.selectBestLocation: equal priority kept the oldest queued fix -> newest
 *  J2  TmapNaviLocationManager.onLocationChanged: drop a fused fix while gps is flowing (extension UbxTmap.accept)
 */

private const val UT = "Lapp/kmaps/extension/tmap/UbxTmap;"
private const val LOC = "Lcom/skt/tmap/engine/navigation/location"

internal val TMAP_SITES: List<Site> = listOf(
    Site(
        cls = "$LOC/GpsProvider;", note = "J1 gps 100 ms", desc = null, count = 1,
        anchor = listOf(
            "const-wide/16 *, 0x3e8",
            "const/4 *, 0x0",
            "invoke-virtual/range {*}, Landroid/location/LocationManager;->requestLocationUpdates(Ljava/lang/String;JFLandroid/location/LocationListener;Landroid/os/Looper;)V",
        ),
        ops = listOf(Op("R", 0, "const-wide/16 {A0}, 0x64")), labels = emptyMap(),
    ),
    Site(
        cls = "$LOC/LocationReliabilityChecker;", note = "J3 gps interval exempt", desc = "(Landroid/location/Location;)Z", count = 1,
        anchor = listOf(
            "invoke-static {*}, Lcom/skt/tmap/engine/navigation/util/TmapExtenstionKt;->getSatelliteCount(Landroid/location/Location;)I",
            "move-result *",
            "const/4 *, 0x4",
            "if-lt *, *, L",
        ),
        ops = listOf(Op("R", 2, "const/4 {A2}, 0x0")), labels = emptyMap(),
    ),
    Site(
        cls = "$LOC/V2FilterConfig;", note = "J4 ignore window 80 ms", desc = "()I", count = 2,   // getter + componentN of the data class
        anchor = listOf("iget *, *, $LOC/V2FilterConfig;->ignoreTimeAfterLocationReceived:I", "return *"),
        ops = listOf(Op("R", 0, "const/16 {A0}, 0x50")), labels = emptyMap(),
    ),
    Site(
        cls = "$LOC/V2FilterConfig;", note = "J5 max rejects per second", desc = "()I", count = 2,   // getter + componentN of the data class
        anchor = listOf("iget *, *, $LOC/V2FilterConfig;->maxConsecutiveReject:I", "return *"),
        ops = listOf(Op("I", 1, "invoke-static {{A0}}, $UT->perSecond(I)I\nmove-result {A0}")), labels = emptyMap(),
    ),
    Site(
        cls = "$LOC/LocationPrioritySelector;", note = "J7 newest of equal priority", count = 1,
        desc = "(Ljava/util/List;Z)Landroid/location/Location;",
        anchor = listOf(
            "invoke-virtual {*}, $LOC/LocationPrioritySelector\$LocationPriority;->getPriority(Z)I",
            "move-result *",
            "if-le *, *, L",
            "move-object *, *",
        ),
        // if-le a, b -> if-lt a, b: the original branch is skipped by the inserted code
        ops = listOf(Op("CF", 2, "if-lt {A2}, {B2}, :ubx_t\ngoto :ubx_n")),
        labels = mapOf("ubx_t" to ("T" to "2"), "ubx_n" to ("K" to "3")),
    ),
    Site(
        cls = "src:TmapNaviLocationManager.java", note = "J2 fused while gps", count = 1,
        desc = "(Landroid/location/Location;)V",
        anchor = listOf(
            "move-object/from16 *, p0",
            "iget-object *, *, $LOC/TmapLocationManager;->context:Landroid/content/Context;",
        ),
        ops = listOf(
            Op("I", 0, "invoke-static/range {p1 .. p1}, $UT->accept(Landroid/location/Location;)Z\nmove-result v0\nif-nez v0, :ubx_go\nreturn-void"),
        ),
        labels = mapOf("ubx_go" to ("K" to "0")),
    ),
)

@Suppress("unused")
private object TmapRes

private const val NAVSDK = "lib/arm64-v8a/libNavigationSDK.so"

private fun sha256(b: ByteArray): String =
    java.security.MessageDigest.getInstance("SHA-256").digest(b).joinToString("") { "%02x".format(it) }

private fun hex(s: String): ByteArray = ByteArray(s.length / 2) { s.substring(2 * it, 2 * it + 2).toInt(16).toByte() }

/**
 * N2: time-weighted fix counters in the native engine libNavigationSDK.so (arm64). The byte list is built from
 * tools/tmap/src (cave code + branch stubs, docs/tmap/N2_patch.md); every entry is checked against the original
 * bytes, and the whole file against the expected input and output hashes.
 */
private fun patchNavigationSdk(log: (String) -> Unit) {
    val list = TmapRes::class.java.classLoader.getResourceAsStream("tmap/navsdk_11.8.4.4075.txt")
        ?.bufferedReader()?.readLines() ?: throw PatchException("tmap/navsdk_11.8.4.4075.txt missing")
    val head = list.filter { !it.startsWith("#") }.associate { it.substringBefore(' ') to it.substringAfter(' ') }
    if (listApkEntries(NAVSDK).isEmpty()) {
        throw PatchException("$NAVSDK not in the APK: patch the whole bundle (.apkm), not only base.apk")
    }
    val file = resourceFile(NAVSDK)
    val data = file.readBytes()
    if (sha256(data) != head["sha256_in"]) throw PatchException("$NAVSDK: unexpected sha256 ${sha256(data)}")
    var n = 0
    for (line in list) {
        val f = line.split(' ')
        if (line.startsWith("#") || f.size < 4 || f[0].toIntOrNull() == null) continue
        val off = f[0].toInt()
        val orig = hex(f[1])
        val new = hex(f[2])
        if (!data.copyOfRange(off, off + orig.size).contentEquals(orig)) throw PatchException("$NAVSDK: bytes at $off differ (${f[3]})")
        new.copyInto(data, off)
        n++
    }
    if (sha256(data) != head["sha256_out"]) throw PatchException("$NAVSDK: patched sha256 mismatch")
    file.writeBytes(data)
    log("ok $NAVSDK: $n entries (time-weighted counters), sha256 ${head["sha256_out"]!!.take(16)}")
    // the 32-bit engine is not patched: keep the app arm64-only so it never runs an unpatched engine with 10 Hz input
    val v7 = listApkEntries("lib/armeabi-v7a/")
    v7.forEach { deleteResource(it) }
    if (v7.isNotEmpty()) log("removed ${v7.size} armeabi-v7a libraries (arm64 only)")
}

@Suppress("unused")
val tmapHighRateGnssPatch = patch(
    name = "TMAP high-rate GNSS",
    description = "Lets every GNSS fix (up to 10 Hz) reach the navigation engine and makes the engine's per-fix " +
        "counters count elapsed time. Patch the whole APKM bundle; the result is arm64 only.",
    default = true,
) {
    compatibleWith(COMPATIBILITY_TMAP)
    extendWith("extensions/tmap.mpe")
    execute {
        bytecodeContext.applySites(TMAP_SITES) { println("TMAP high-rate GNSS: $it") }
        patchNavigationSdk { println("TMAP high-rate GNSS: $it") }
    }
}

package app.kmaps.extension.tmap;

import android.content.pm.Signature;
import android.location.Location;
import android.os.SystemClock;

/** TMAP high-rate GNSS helpers, injected by the patch "TMAP high-rate GNSS". */
@SuppressWarnings("unused")
public final class UbxTmap {
    /**
     * The app's ORIGINAL signing certificate (DER, hex) for TMAP 11.8.4.4075.
     * SHA-256(DER) = 90351f2e6ce0c95c3696dde9c090e803c0a0d8e3d64ce53375c9c6003cf0f8e2.
     *
     * The high-rate patch re-signs the APK with a different key. The SK T-ID login library hashes the
     * live signing certificate (com.skt.tid.utils.Utils.getSignatures -> getAppHashKey / getAppKeyHashValue,
     * SHA-256 then Base64) and puts it in the authorize-request deviceInfo; with a re-sign key the hash no
     * longer matches what T-ID registered for the app, so login is refused (no login screen appears).
     * getSignatures is redirected to {@link #signatures()} so that hash is computed from the original
     * certificate for any nonce. android.content.pm.Signature(String) parses the hex and toByteArray()
     * returns the same DER bytes the stock code would have hashed.
     */
    private static final String ORIG_CERT =
        "3082037930820261a0030201020204557b8320300d06092a864886f70d01010b0500306c3110300e06035504061307556e6b6e6f776e3110300e06035504081307556e6b6e6f776e3110300e06035504071307556e6b6e6f776e3110300e060355040a1307556e6b6e6f776e3110300e060355040b1307556e6b6e6f776e3110300e06035504031307556e6b6e6f776e3020170d3134303630323130353133355a180f32303639303330353130353133355a306c3110300e06035504061307556e6b6e6f776e3110300e06035504081307556e6b6e6f776e3110300e06035504071307556e6b6e6f776e3110300e060355040a1307556e6b6e6f776e3110300e060355040b1307556e6b6e6f776e3110300e06035504031307556e6b6e6f776e30820122300d06092a864886f70d01010105000382010f003082010a0282010100865942964e96e62cf5059fc3279e112f053633e540123bd323937e4a6692feeba6ccd7c921d23f5c8d114f5dcfbebd571566c12474bbe24fad3644cea39524d49e137b4799a8e6cc6eee53431530fa019bce38681386f6710739d2afefc2c369b7fb1381a9e115dd416f1be3c309868d20e266756671d2a84b12ba7ad286fdf2de5c6231ca72373794ee860521a98e65ebf312d080894129416efdedda7e5a4fe6bf7de76966e1723dbc2898ee8f72e70bea9400023d5d6c8080bb07b05ff03d21896bb1af03c556c53d5a65e6b195f8f5654428860545574984696303e9fe76fef581d15e700989caec9a32be8711765c0ee6f7c21ddca507dceb8f042831bf0203010001a321301f301d0603551d0e04160414147e5022c025e441a19b33bd08e0275762e0a0aa300d06092a864886f70d01010b050003820101004db9c5bd0cea9f439cd80603e8f3d6028b242fa2e8caa21fd0bf6ce9c5c5e77ef725027af1bcd8e3c3b297d11c761f243cf91e4046076545540f318c6963790def126ed08ec83e6c722443bb59b77df95096aa349fd32f459941384919e06df03fb33c8a846b6263c45daefd5c255769a51ab239e1307ebbddab9e40b3cf108edc22cb0e74a32634185d32a262af945c9bba5dcd4acece0c32a9d4a192bd3ba8ed7d8e80a9d4ca69db4a2b3d112f01fdc1d78de36a7bd6837b4ab785bb56b7260867539f46ac2e00b54e71725c1fbfb39bf4e29ade3597e5b58898993ece030061a0afa35dd24d308295da355f0f03f094483e12f0015d0854178d9752ee639f";

    /** The original signing certificate(s) the T-ID login library should hash instead of the re-sign key. */
    public static Signature[] signatures() {
        return new Signature[]{ new Signature(ORIG_CERT) };
    }
    /** elapsedRealtime of the last gps fix seen by TmapNaviLocationManager, 0 = none yet. */
    private static long lastGpsMs;
    /** smoothed interval between gps fixes (ms); starts at the stock 1 Hz. */
    private static double emaIntervalMs = 1000.0;

    /**
     * Called first in TmapNaviLocationManager.onLocationChanged. Tracks the gps fix rate and drops a fused fix
     * while gps is flowing (a 1 Hz fused fix between 10 Hz gps fixes jumps the position back and forth; the stock
     * V2 filter only separated them by its 900 ms window, which the patch shortens). Returns false to drop.
     */
    public static boolean accept(Location location) {
        if (location == null) return true;           // the original method handles null itself
        long now = SystemClock.elapsedRealtime();
        String provider = location.getProvider();
        if ("gps".equals(provider)) {
            if (lastGpsMs != 0) {
                long dt = now - lastGpsMs;
                if (dt < 50) dt = 50;
                if (dt > 1000) dt = 1000;
                emaIntervalMs = emaIntervalMs * 0.8 + dt * 0.2;
            }
            lastGpsMs = now;
            return true;
        }
        if ("fused".equals(provider)) {
            return lastGpsMs == 0 || now - lastGpsMs > 2000;
        }
        return true;
    }

    /** A count meant as "n fixes = n seconds" at the stock 1 Hz, scaled to the current gps rate (never below n). */
    public static int perSecond(int n) {
        long scaled = Math.round(n * 1000.0 / emaIntervalMs);
        return (int) Math.max(n, Math.min(scaled, (long) n * 20));
    }
}

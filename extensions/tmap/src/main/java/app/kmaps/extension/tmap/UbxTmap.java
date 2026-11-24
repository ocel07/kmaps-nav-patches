package app.kmaps.extension.tmap;

import android.location.Location;
import android.os.SystemClock;

/** TMAP high-rate GNSS helpers, injected by the patch "TMAP high-rate GNSS". */
@SuppressWarnings("unused")
public final class UbxTmap {
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

/*
 * TCSS 142 - Programming Principles
 * SurgeTester (strict, oracle-based) for Project 2
 *
 * This tester does NOT parse console output. It calls the required methods and
 * compares them to an internal reference implementation derived from the spec.
 *
 * What it checks:
 *   - computeSurgeMultiplier: time, weather, market, clamping
 *   - computeTotalFare: baseTrip, surge, rounding to 2 decimals
 *   - classifySurge: exact strings at boundaries
 *   - recommendAction: exact strings aligned with thresholds
 *
 * Strategy:
 *   1) Golden (deterministic) cases covering boundaries and combinations
 *   2) Randomized property checks (reproducible seed)
 */

import java.util.Random;

public class SurgeTester {
    private static int total = 0;
    private static int passed = 0;

    // Tight tolerances; we expect exact doubles in most cases after rounding.
    private static final double EPS = 1e-9;

    public static void main(String[] args) {
        line("=== SurgeSimulator Strict Auto Tester ===");

        section("[A] Golden cases (deterministic)");
        goldenCases();

        section("[B] Classification + Recommendation boundaries");
        classificationBoundaries();

        section("[C] Randomized property tests (seeded)");
        randomChecks();

        line("");
        summary();
    }

    // -------------------- GOLDEN CASES --------------------

    private static void goldenCases() {
        // Pure time effect (neutral market, CLEAR)
        gold("DAY +0.00",       "DAY","CLEAR",3,5, 1.00);
        gold("MORNING +0.10",   "MORNING","CLEAR",3,5, 1.10);
        gold("EVENING +0.20",   "EVENING","CLEAR",3,5, 1.20);
        gold("NIGHT +0.15",     "NIGHT","CLEAR",3,5, 1.15);

        // Weather
        gold("RAIN +0.15",      "DAY","RAIN",3,5, 1.15);

        // Market: severe / elevated / soft
        gold("Severe +0.40",    "DAY","CLEAR",5,1, 1.40);
        gold("Elevated +0.25",  "DAY","CLEAR",3,3, 1.25);
        gold("Soft  -0.10→clamp","DAY","CLEAR",1,5, 1.00); // would be 0.90, clamp up

        // Combination from handout sanity check
        // EVENING(+0.20) + RAIN(+0.15) + Severe(+0.40) = 1.75
        double surge = SurgeSimulator.computeSurgeMultiplier("EVENING","RAIN",5,1);
        checkApprox("EVENING+RAIN+Severe -> 1.75", surge, 1.75, EPS);

        // Fare rounding from handout: base=12, miles=7.5 ⇒ baseTrip=23.25, surge=1.75
        // total = 23.25*1.75 = 40.6875 → 40.69
        double totalFare = SurgeSimulator.computeTotalFare(12.00, 7.5, 1.75);
        checkApprox("Total fare rounding (40.69)", totalFare, 40.69, EPS);

        // Cross-check classification/recommendation with the same surge
        checkEquals("classify(1.75) → High Surge",
                SurgeSimulator.classifySurge(1.75),
                refClassify(1.75));
        checkEquals("recommend(1.75) → High surge message",
                SurgeSimulator.recommendAction(1.75),
                refRecommend(1.75));
    }

    private static void gold(String label, String time, String weather, int demand, int drivers,
                             double expectedSurge) {
        double actual = SurgeSimulator.computeSurgeMultiplier(time, weather, demand, drivers);
        checkApprox(label, actual, expectedSurge, EPS);
        // Verify clamped range always
        checkTrue("    clamped [1.0,3.0]", actual >= 1.0 - EPS && actual <= 3.0 + EPS);
    }

    // -------------------- CLASSIFICATION BOUNDARIES --------------------

    private static void classificationBoundaries() {
        // Exact thresholds: <1.20 Normal, [1.20, 1.60) Moderate, >=1.60 High
        checkEquals("classify(1.19) → Normal",
                SurgeSimulator.classifySurge(1.19), "Normal");
        checkEquals("classify(1.20) → Moderate Surge",
                SurgeSimulator.classifySurge(1.20), "Moderate Surge");
        checkEquals("classify(1.59) → Moderate Surge",
                SurgeSimulator.classifySurge(1.59), "Moderate Surge");
        checkEquals("classify(1.60) → High Surge",
                SurgeSimulator.classifySurge(1.60), "High Surge");

        // Recommendation must EXACTLY match spec strings:
        checkEquals("recommend(1.10) → Normal msg",
                SurgeSimulator.recommendAction(1.10),
                "Normal demand - book now.");
        checkEquals("recommend(1.35) → Moderate msg",
                SurgeSimulator.recommendAction(1.35),
                "Moderate surge - book if you are in a hurry.");
        checkEquals("recommend(1.80) → High msg",
                SurgeSimulator.recommendAction(1.80),
                "High surge - consider waiting 10 minutes.");
    }

    // -------------------- RANDOMIZED PROPERTY TESTS --------------------

    private static void randomChecks() {
        Random rnd = new Random(142L); // reproducible

        String[] times = {"MORNING","DAY","EVENING","NIGHT"};
        String[] weathers = {"CLEAR","RAIN"};

        int N = 50;; // plenty, but fast
        int localPass = 0;
        for (int i = 0; i < N; i++) {
            String t = times[rnd.nextInt(times.length)];
            String w = weathers[rnd.nextInt(weathers.length)];
            int demand = 1 + rnd.nextInt(5);   // 1..5
            int drivers = 1 + rnd.nextInt(5);  // 1..5
            double base = 5.0 + rnd.nextDouble() * (100.0 - 5.0);
            double miles = 0.10 + rnd.nextDouble() * (100.0 - 0.10);

            double surgeExp = refMultiplier(t, w, demand, drivers);
            double surgeAct = SurgeSimulator.computeSurgeMultiplier(t, w, demand, drivers);
            checkApprox("surge oracle", surgeAct, surgeExp, EPS);

            double totalExp = refTotal(base, miles, surgeExp);
            double totalAct = SurgeSimulator.computeTotalFare(base, miles, surgeAct);
            checkApprox("total oracle", totalAct, totalExp, EPS);

            String cExp = refClassify(surgeExp);
            String cAct = SurgeSimulator.classifySurge(surgeAct);
            checkEquals("classify oracle", cAct, cExp);

            String rExp = refRecommend(surgeExp);
            String rAct = SurgeSimulator.recommendAction(surgeAct);
            checkEquals("recommend oracle", rAct, rExp);

            // Safety properties
            checkTrue("surge in [1,3]", surgeAct >= 1.0 - EPS && surgeAct <= 3.0 + EPS);
            checkTrue("total ≥ 0", totalAct >= -EPS);

            localPass++;
        }
        line("  Random cases executed: " + localPass);
    }

    // -------------------- ORACLE (SPEC) --------------------

    private static double refMultiplier(String timeBlock, String weather, int demand, int drivers) {
        double m = 1.0;

        // Time
        if ("MORNING".equals(timeBlock)) m += 0.10;
        else if ("EVENING".equals(timeBlock)) m += 0.20;
        else if ("NIGHT".equals(timeBlock)) m += 0.15;
        // DAY adds 0.00

        // Weather
        if ("RAIN".equals(weather)) m += 0.15;

        // Market
        if (demand >= 4 && drivers <= 2) {
            m += 0.40;
        } else if (demand >= 3 && drivers <= 3) {
            m += 0.25;
        } else if (demand <= 2 && drivers >= 4) {
            m -= 0.10;
        }

        // Clamp
        if (m < 1.0) m = 1.0;
        if (m > 3.0) m = 3.0;
        return m;
    }

    private static double refTotal(double baseFare, double miles, double surge) {
        double perMile = 1.50; // per spec
        double baseTrip = baseFare + perMile * miles;
        double t = baseTrip * surge;
        return round2(t);
    }

    private static String refClassify(double m) {
        if (m < 1.20) return "Normal";
        else if (m < 1.60) return "Moderate Surge";
        else return "High Surge";
    }

    private static String refRecommend(double m) {
        if (m < 1.20) return "Normal demand - book now.";
        else if (m < 1.60) return "Moderate surge - book if you are in a hurry.";
        else return "High surge - consider waiting 10 minutes.";
    }

    // -------------------- ASSERT HELPERS --------------------

    private static void section(String title) {
        line("");
        System.out.println(title);
    }

    private static void line(String s) {
        System.out.println(s);
    }

    private static void checkApprox(String label, double actual, double expected, double eps) {
        total++;
        boolean ok = Math.abs(actual - expected) <= eps;
        if (ok) {
            passed++;
            System.out.printf("  ✓ %s  actual=%.6f  expected=%.6f%n", label, actual, expected);
        } else {
            System.out.printf("  ✗ %s  actual=%.6f  expected=%.6f  diff=%.6g%n",
                    label, actual, expected, (actual - expected));
        }
    }

    private static void checkEquals(String label, String actual, String expected) {
        total++;
        boolean ok = expected.equals(actual);
        if (ok) {
            passed++;
            System.out.printf("  ✓ %s  actual=\"%s\"%n", label, actual);
        } else {
            System.out.printf("  ✗ %s  actual=\"%s\"  expected=\"%s\"%n", label, actual, expected);
        }
    }

    private static void checkTrue(String label, boolean condition) {
        total++;
        if (condition) {
            passed++;
            System.out.printf("  ✓ %s%n", label);
        } else {
            System.out.printf("  ✗ %s%n", label);
        }
    }

    private static void summary() {
        System.out.printf("Passed %d of %d checks.%n", passed, total);
        if (passed == total) {
            System.out.println("All checks passed ✅");
        } else {
            System.out.println("Some checks failed ❌ — see details above.");
        }
    }

    private static double round2(double x) {
        return Math.round(x * 100.0) / 100.0;
    }
}


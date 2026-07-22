package top.socialbot.tools;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.PrintWriter;
import java.io.StringWriter;
import java.util.*;

public class SystemTool {
    private final static Logger logger = LoggerFactory.getLogger("SystemTool");

    public static Random rand = new Random(new Date().getTime());

    /**
     * 提取异常信息到一个字符串，便于在log中记录
     * @param throwable 异常对象
     * @return 字符串
     */
    public static String getStackTrace(Throwable throwable) {
        StringWriter stringWriter = new StringWriter();
        PrintWriter printWriter = new PrintWriter(stringWriter);
        throwable.printStackTrace(printWriter);
        String stackTrace = stringWriter.toString();
        stackTrace = stackTrace
                .replaceAll("\\r\\n", " => ")
                .replaceAll("\\n", " => ");
        return stackTrace;
    }

    public static <T> T getDiscreteRandom(List<T> values, List<Double> weights) {
        if (weights == null || weights.isEmpty() || weights.size() != values.size()) {
            return values.get(rand.nextInt(values.size()));
        }
        double sum = 0.0;
        for (double value : weights) {
            sum += value;
        }
        if (sum <= 0.0) {
            return values.get(rand.nextInt(values.size()));
        }
        double r = rand.nextDouble();
        double cumsum = 0.0;
        for (int i = 0; i < weights.size(); i++) {
            cumsum += (weights.get(i) / sum);
            if (cumsum >= r) {
                return values.get(i);
            }
        }
        return values.getLast();
    }

    public static void main(String[] args) {
        Map<Integer, Integer> count = new HashMap<>();
        for (int r = 0; r < 100000; r++) {
            int i = getDiscreteRandom(List.of(114, 214, 314, 414), List.of(1.0, 2.0, 3.0));
            count.putIfAbsent(i, 0);
            count.computeIfPresent(i, (k, v) -> v + 1);
        }
        for (int k : count.keySet()) {
            System.out.println(k + ": " + count.get(k) / 100000.0);
        }
    }
}

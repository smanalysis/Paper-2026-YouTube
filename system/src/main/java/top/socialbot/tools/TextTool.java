package top.socialbot.tools;

import org.apache.commons.text.similarity.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.zip.GZIPInputStream;
import java.util.zip.GZIPOutputStream;

public class TextTool {
    private final static Logger logger = LoggerFactory.getLogger("TextTool");

    /**
     * 解析文本，获得xml对象
     * @param source xml的文本
     * @return xml的Document
     */
    public static org.w3c.dom.Document parseXML(String source) {
        try {
            // 解析XML
            DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
            DocumentBuilder builder = factory.newDocumentBuilder();
            return builder.parse(new ByteArrayInputStream(source.getBytes()));
        } catch (Exception e) {
            logger.warn(SystemTool.getStackTrace(e));
            return null;
        }
    }

    //TODO Apache Commons-Text提供了对于字符串距离的计算方法，引入并对结果做归一化处理
    public enum DistanceMethod {
        Cosine,
        JaccardDistance,
        JaroWinkler,
        Levenshtein,
        LongestCommonSubsequence
    }

    public static double textSimilarity(String text1, String text2, DistanceMethod method) {
        return 1 - switch (method) {
            case Cosine -> new CosineDistance().apply(text1, text2) / 2.0;
            case JaccardDistance -> new JaccardDistance().apply(text1, text2);
            case JaroWinkler -> new JaroWinklerDistance().apply(text1, text2);
            case Levenshtein -> new LevenshteinDistance().apply(text1, text2) / (double) Math.max(text1.length(), text2.length());
            case LongestCommonSubsequence -> new LongestCommonSubsequenceDistance().apply(text1, text2) / (double) (text1.length() + text2.length());
        };
    }

    public static String compress(String str) {
        if (str == null || str.isEmpty()) {
            return str;
        }
        try (ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
             GZIPOutputStream gzipStream = new GZIPOutputStream(outputStream)) {
            gzipStream.write(str.getBytes(StandardCharsets.UTF_8));
            gzipStream.finish();
            byte[] compressedData = outputStream.toByteArray();
            return Base64.getEncoder().encodeToString(compressedData);
        } catch (Exception e) {
            logger.warn(SystemTool.getStackTrace(e));
            return "";
        }
    }

    public static String decompress(String compressedBase64Str) {
        if (compressedBase64Str == null || compressedBase64Str.isEmpty()) {
            return compressedBase64Str;
        }
        try {
            // 1. Base64 解码 → 得到压缩后的字节数组
            byte[] compressedBytes = Base64.getDecoder().decode(compressedBase64Str);
            // 2. GZIP 解压 → 读取字节流
            ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
            try (ByteArrayInputStream inputStream = new ByteArrayInputStream(compressedBytes);
                 GZIPInputStream gzipStream = new GZIPInputStream(inputStream)) {
                byte[] buffer = new byte[1024];
                int len;
                while ((len = gzipStream.read(buffer)) > 0) {
                    outputStream.write(buffer, 0, len);
                }
            }
            // 3. 转为原始字符串（UTF-8）
            return outputStream.toString(StandardCharsets.UTF_8);
        } catch (Exception e) {
            logger.warn(SystemTool.getStackTrace(e));
            return "";
        }
    }
}

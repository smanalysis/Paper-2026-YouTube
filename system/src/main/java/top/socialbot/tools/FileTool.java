package top.socialbot.tools;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.alibaba.fastjson2.JSONWriter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Paths;
import java.util.*;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import java.util.zip.ZipOutputStream;

public class FileTool {
    private final static Logger logger = LoggerFactory.getLogger("FileTools");

    /**
     * 以UTF8编码，将一组字符串按行重新写入一个文件。
     * @param lines 字符串组
     * @param filePath 目标文件
     */
    public static <T> void writeFile(List<T> lines, String filePath) {
        try (BufferedWriter writer = new BufferedWriter(
                new OutputStreamWriter(
                        new FileOutputStream(filePath, false),
                        StandardCharsets.UTF_8))) {
            for (Object line : lines) {
                writer.write(line.toString());
                writer.newLine();
            }
        } catch (Exception e) {
            logger.warn(SystemTool.getStackTrace(e));
        }
    }

    /**
     * 以UTF8编码，将一组字符串按行追加写入一个文件。
     * @param lines 字符串组
     * @param filePath 目标文件
     */
    public static void appendFile(List<String> lines, String filePath) {
        try (BufferedWriter writer = new BufferedWriter(
                new OutputStreamWriter(
                        new FileOutputStream(filePath, true),
                        StandardCharsets.UTF_8))) {
            for (String line : lines) {
                writer.write(line);
                writer.newLine();
            }
        } catch (Exception e) {
            logger.warn(SystemTool.getStackTrace(e));
        }
    }

    /**
     * 以UTF8编码，按行读取一个文件的所有内容到一个字符串列表。
     * @param filePath 目标文件
     * @return 字符串列表
     */
    public static List<String> readFileLines(String filePath) {
        List<String> results = new ArrayList<>();
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(
                        new FileInputStream(filePath),
                        StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                results.add(line);
            }
        } catch (Exception e) {
            logger.warn(SystemTool.getStackTrace(e));
        }
        return results;
    }

    public static String readFile(String filePath) {
        List<String> liens = readFileLines(filePath);
        StringBuilder result = new StringBuilder();
        for (String line : liens) {
            result.append(line);
            result.append(System.lineSeparator());
        }
        return result.toString();
    }

    /**
     * 以迭代器方式逐行读取一个文本文件，避免一次性读取对于内存的占用。
     */
    public static class LineIterator implements Iterator<String>, AutoCloseable {
        private final BufferedReader reader;
        private String nextLine;
        private boolean isClosed;

        public LineIterator(String path) throws IOException {
            reader = new BufferedReader(new InputStreamReader(new FileInputStream(Paths.get(path).toFile()), StandardCharsets.UTF_8));
                    // Files.newBufferedReader(Paths.get(path), StandardCharsets.UTF_8);
            // Initialize with the first line
            nextLine = reader.readLine();
            isClosed = false;
        }

        @Override
        public boolean hasNext() {
            return nextLine != null;
        }

        @Override
        public String next() {
            if (isClosed) {
                nextLine = null;
                return null;
            };
            String line = nextLine;
            try {
                // Read next line for subsequent calls
                nextLine = reader.readLine();
                if (nextLine == null) {
                    // Close the reader if we've reached the end of the file
                    close();
                }
            } catch (IOException e) {
                close();
                logger.warn(SystemTool.getStackTrace(e));
            }
            return line;
        }

        @Override
        public void close() {
            if (reader != null) {
                try {
                    reader.close();
                    isClosed = true;
                } catch (IOException e) {
                    logger.warn(SystemTool.getStackTrace(e));
                }
            }
        }
    }

    /**
     * 以迭代器方式逐行读取一个ZIP文本中的所有文件，避免一次性读取对于内存的占用。
     */
    public static class ZipTextFilesIterator implements Iterator<String>, AutoCloseable {
        private final String extension;
        private ZipFile zipFile;
        private List<ZipEntry> entries;
        private int index;

        private BufferedReader currentReader;
        private String nextLine;

        public ZipTextFilesIterator(String zipFilePath, String extension) throws IOException {
            this.extension = extension;
            try {
                zipFile = new ZipFile(zipFilePath);
                // Extracting the zip entries and sorting them by modified time
                entries = new ArrayList<>();
                zipFile.stream().forEach(entries::add);
                entries.sort(Comparator.comparingLong(ZipEntry::getTime));
            } catch (Exception e) {
                logger.warn(SystemTool.getStackTrace(e));
            }
            //
            index = -1;
            advanceToNextTextFile();
        }

        private void advanceToNextTextFile() throws IOException {
            if (currentReader != null) {
                currentReader.close();
                currentReader = null;
            }
            //
            if (++index < entries.size()) {
                do {
                    if (entries.get(index).getName().endsWith(extension)
                            && !entries.get(index).isDirectory()) {
                        currentReader = new BufferedReader(
                                new InputStreamReader(
                                        zipFile.getInputStream(entries.get(index)),
                                        StandardCharsets.UTF_8));
                        nextLine = currentReader.readLine();
                        if (nextLine != null) {
                            return;
                        }
                    }
                } while (++index < entries.size());
            }
            nextLine = null;
        }

        @Override
        public boolean hasNext() {
            if (nextLine == null) {
                // 没有下一个了，直接关闭
                close();
            }
            return nextLine != null;
        }

        @Override
        public String next() {
            String line = nextLine;
            try {
                nextLine = currentReader.readLine();
                if (nextLine == null) {
                    advanceToNextTextFile();
                }
            } catch (IOException e) {
                close();
                logger.warn(SystemTool.getStackTrace(e));
            }
            return line;
        }

        @Override
        public void close() {
            if (currentReader != null) {
                try {
                    currentReader.close();
                    zipFile.close();
                } catch (IOException e) {
                    logger.warn(SystemTool.getStackTrace(e));
                }
            }
        }
    }

    /**
     * 写入一个Java Serializable对象写入文件中。
     * @param object 待写入对象
     * @param filePath 目标文件
     */
    public static void writeObject(Serializable object, String filePath) {
        try (ObjectOutputStream oos = new ObjectOutputStream(new FileOutputStream(filePath))) {
            oos.writeObject(object);
        } catch (IOException e) {
            logger.warn(SystemTool.getStackTrace(e));
        }
    }

    /**
     * 读取目标文件中的一个Java Serializable对象。
     * @param filePath 目标文件
     */
    public static Object loadObject(String filePath) {
        try (ObjectInputStream oos = new ObjectInputStream(new FileInputStream(filePath))) {
            return oos.readObject();
        } catch (Exception e) {
            logger.warn(SystemTool.getStackTrace(e));
            return null;
        }
    }

    public static void saveJSONObject(Object obj, String filePath) {
        writeFile(Collections.singletonList(JSON.toJSONString(obj, JSONWriter.Feature.PrettyFormat, JSONWriter.Feature.WriteMapNullValue)), filePath);
    }

    public static JSONObject loadJSONObject(String filePath) {
        try {
            return JSON.parseObject(new FileInputStream(filePath));
        } catch (FileNotFoundException e) {
            logger.warn(SystemTool.getStackTrace(e));
            return null;
        }
    }


    public static String readInputStream(InputStream is) {
        StringBuilder sb = new StringBuilder();
        try (InputStreamReader streamReader = new InputStreamReader(is, StandardCharsets.UTF_8);
             BufferedReader reader = new BufferedReader(streamReader)) {
            String line;
            while ((line = reader.readLine()) != null) {
                sb.append(line);
                sb.append("\n");
            }
        } catch (Exception e) {
            SystemTool.getStackTrace(e);
        }
        return sb.toString();
    }

    /**
     * 创建打包zip文件，不包含目录结构
     * @param files 待打包文件
     * @param outputZip 输出的打包文件
     * @throws IOException 异常
     */
    public static boolean zip(File[] files, File outputZip) {
        // Create a buffer for reading the files
        byte[] buffer = new byte[1024];

        // Create a ZIP output stream
        try (FileOutputStream fos = new FileOutputStream(outputZip);
             ZipOutputStream zos = new ZipOutputStream(fos)) {

            for (File file : files) {
                if (!file.exists() || !file.isFile()) {
                    System.out.println("Skipping invalid file: " + file.getName());
                    continue;
                }

                // Add a new entry to the ZIP file
                try (FileInputStream fis = new FileInputStream(file)) {
                    ZipEntry zipEntry = new ZipEntry(file.getName());
                    zos.putNextEntry(zipEntry);

                    // Write file content to the ZIP output stream
                    int length;
                    while ((length = fis.read(buffer)) > 0) {
                        zos.write(buffer, 0, length);
                    }

                    // Close the current entry
                    zos.closeEntry();
                }
            }

            return true;
        } catch (Exception e) {
            logger.warn(SystemTool.getStackTrace(e));
            return false;
        }
    }
}

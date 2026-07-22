package com.socimata.experiment.youtube;

import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.alibaba.fastjson2.JSON;
import com.google.api.client.googleapis.GoogleUtils;
import com.google.api.client.http.javanet.NetHttpTransport;
import com.google.api.client.json.JsonFactory;
import com.google.api.client.json.gson.GsonFactory;
import com.google.api.services.youtube.YouTube;
import com.google.api.services.youtube.YouTubeRequestInitializer;
import com.socimata.experiment.BrowseClient;
import com.teamdev.jxbrowser.browser.Browser;
import com.teamdev.jxbrowser.dom.Document;
import com.teamdev.jxbrowser.dom.Element;
import com.teamdev.jxbrowser.frame.Frame;
import com.teamdev.jxbrowser.ui.KeyCode;
import com.teamdev.jxbrowser.ui.event.KeyPressed;
import com.teamdev.jxbrowser.ui.event.KeyReleased;
import com.teamdev.jxbrowser.ui.event.KeyTyped;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import top.socialbot.tools.FileTool;
import top.socialbot.tools.SystemTool;

import java.io.IOException;
import java.net.*;
import java.security.GeneralSecurityException;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;

@SuppressWarnings("unused")
public class YoutubeTools {
    /**
     * YouTube Video Categories:
     * ID:  1 | Title: Film & Animation
     * ID:  2 | Title: Autos & Vehicles
     * ID: 10 | Title: Music
     * ID: 15 | Title: Pets & Animals
     * ID: 17 | Title: Sports
     * ID: 18 | Title: Short Movies
     * ID: 19 | Title: Travel & Events
     * ID: 20 | Title: Gaming
     * ID: 21 | Title: Videoblogging
     * ID: 22 | Title: People & Blogs
     * ID: 23 | Title: Comedy
     * ID: 24 | Title: Entertainment
     * ID: 25 | Title: News & Politics
     * ID: 26 | Title: Howto & Style
     * ID: 27 | Title: Education
     * ID: 28 | Title: Science & Technology
     * ID: 29 | Title: Nonprofits & Activism
     */
    private static final Logger logger = LoggerFactory.getLogger("YoutubeTools");

    private static final Random rand = new Random(new Date().getTime());

    public static void main(String[] args) throws Exception {
        /*
        List<String> ids = FileTool.readFileLines("./videos.txt");
        int batchSize = 50;
        for (int i = 91600; i < ids.size(); i = i + batchSize) {
            System.out.println(i);
            List<String> batch = ids.subList(i, Math.min(i + batchSize, ids.size()));
            getCategoryId(batch, "127.0.0.1", 7890);
            //noinspection BusyWait
            Thread.sleep(5000);
        }*/

        String tag = "| YoutubeTools |";
        List<String> lines = FileTool.readFileLines("./_log/exp_back.1.log");
        List<String> results = new ArrayList<>();
        for (String line : lines) {
            String v = line.substring(line.indexOf(tag) + tag.length()).trim();
            JSONArray array = JSON.parseArray(v);
            for (int i = 0; i < array.size(); i++) {
                results.add(JSON.toJSONString(array.get(i)));
            }
        }
        FileTool.writeFile(results, "./details1.jsonl");
    }

    private static final String APPLICATION_NAME = "API code samples";
    private static final JsonFactory JSON_FACTORY = GsonFactory.getDefaultInstance();
    private static final String[] API_KEYS = {"AIzaSyCUye0jV1BEFsaMDjR8bYIEHUxKRi4EWAY",
            "AIzaSyCXW_qV2gWTaUTHAGWAwD3F2t0k0nmmhic",
            "AIzaSyASoHGyT3RGiKVAXz3G2rX85_58tj4r6lc",
            "AIzaSyAd_fXk8oesb9KCJ4n4IJmpiT9fRTlFunY"};
    private static int keyIndex = 1;
    private static final Lock lock = new ReentrantLock();

    /**
     * 创建并返回一个用于访问 YouTube API 的 YouTube 服务对象。
     * 该方法需要 Google API 的授权和网络传输配置，同时需要设置有效的 API 密钥。
     *
     * @return YouTube 服务对象，用于进行 YouTube API 的请求。
     */
    private static YouTube getServiceFromAPI(String proxyAddr, int port) throws IOException, GeneralSecurityException {
        // 使用 GoogleNetHttpTransport.newTrustedTransport() 创建一个安全的 HTTP 传输对象
        // 配置代理设置
        Proxy proxy = new Proxy(Proxy.Type.HTTP, new InetSocketAddress(proxyAddr, port));
        // 创建带有代理配置的 HTTP 传输
        NetHttpTransport httpTransport = new NetHttpTransport.Builder()
                .setProxy(proxy)
                .trustCertificates(GoogleUtils.getCertificateTrustStore())
                .build();
        // 创建一个 YouTube.Builder 对象，并配置 YouTube 服务
        return new YouTube.Builder(httpTransport, JSON_FACTORY, null)
                .setYouTubeRequestInitializer(new YouTubeRequestInitializer(API_KEYS[keyIndex])) // 设置 API 密钥
                .setApplicationName(APPLICATION_NAME) // 设置应用程序名称
                .build(); // 构建并返回 YouTube 服务对象
    }

    /**
     * 根据给定的 CrowItem 列表，通过 YouTube API 获取视频的分类信息，并将官方的分类ID存储到各个 CrowItem 对象的itemPreferTag中。
     *
     * @param videoIds 包含 CrowItem 对象的列表，每个对象需要填充视频分类信息。
     */
    public static Map<String, Integer> getCategoryId(List<String> videoIds, String proxyAddr, int port) {
        try {
            lock.lock();
            YouTube youtubeService = getServiceFromAPI(proxyAddr, port);
            YouTube.Videos.List request = youtubeService.videos().list("contentDetails, snippet, statistics, topicDetails");
            String idStr = String.join(",", videoIds);
            String a = request.setId(idStr).execute().getItems().toString();
            logger.info(a);
            // 将 JSON 字符串解析为 JsonArray
            List<Video> videos = JSONArray.parseArray(a).toJavaList(Video.class);
            Map<String, Integer> result = new HashMap<>();
            for (Video video : videos) {
                result.put(video.id, Integer.parseInt(video.snippet.categoryId));
            }
            return result;
        } catch (Exception e) {
            keyIndex = ++keyIndex % API_KEYS.length;
            throw new RuntimeException(e.getMessage());
        } finally {
            lock.unlock();
        }
    }

    /**
     * 测试网络是否可用（支持代理）
     *
     * @param proxyAddr 代理主机（如 "192.168.1.100"）
     * @param proxyPort 代理端口（如 8080）
     * @return 是否可访问
     */
    public static boolean isNetworkAvailable(String proxyAddr, int proxyPort) {
        try {
            // 1. 使用 URI 解析 URL（避免直接使用 new URL(String)）
            URI uri = new URI("https://www.youtube.com/?persist_gl=1&gl=US");
            URL validUrl = uri.toURL();
            // 2. 创建代理对象
            Proxy proxy;
            if (proxyAddr != null && !proxyAddr.isEmpty() && proxyPort > 0) {
                proxy = new Proxy(Proxy.Type.HTTP, new InetSocketAddress(proxyAddr, proxyPort));
            } else {
                proxy = Proxy.NO_PROXY;
            }
            // 3. 打开连接（使用代理）
            HttpURLConnection connection = (HttpURLConnection) validUrl.openConnection(proxy);
            // 4. 设置超时（单位：毫秒）
            connection.setConnectTimeout(5000); // 5秒连接超时
            connection.setReadTimeout(5000);   // 5秒读取超时
            // 5. 发起请求并检查状态码
            connection.connect();
            int responseCode = connection.getResponseCode();
            // 6. 返回是否成功（HTTP 200-399 视为成功）
            return (responseCode >= 200 && responseCode < 400);
        } catch (Exception e) {
            System.err.println("网络检测异常: " + e.getMessage());
            return false;
        }
    }

    public static long parseDuration(String timeStr) {
        String[] parts = timeStr.split(":");
        if (parts.length == 3) {
            return Duration.ofHours(Long.parseLong(parts[0]))
                    .plusMinutes(Long.parseLong(parts[1]))
                    .plusSeconds(Long.parseLong(parts[2]))
                    .getSeconds();
        } else if (parts.length == 2) {
            return Duration.ofMinutes(Long.parseLong(parts[0]))
                    .plusSeconds(Long.parseLong(parts[1]))
                    .getSeconds();
        } else {
            return -1;
        }
    }

    public static Map<String, JSONObject> extractVideos(BrowseClient client, Document document) {
        Map<String, JSONObject> viewableVideoIds = new HashMap<>();
        try {
            // 等待加载元素
            List<Element> items = new ArrayList<>();
            for (int i = 0; i < 30; i++) {
                items = document.findElementsByCssSelector("#primary > ytd-rich-grid-renderer > #contents > ytd-rich-item-renderer");
                if (items.size() > 10) {
                    break;
                }
                Thread.sleep(1000);
            }
            client.log(String.format("本次曝光总量: %d", items.size()));
            client.log("获取曝光视频");
            for (Element item : items) {
                try {
                    List<Element> channelElement = item.findElementsByCssSelector("#channel-name a, yt-content-metadata-view-model span > a");
                    if (channelElement.isEmpty()) {
                        client.logSilent(item.outerHtml());
                        client.log("无channel信息");
                        continue;
                    }
                    String channel = channelElement.getFirst().attributeValue("href").trim();
                    if (channel.contains("@")) {
                        channel = channel.substring(channel.indexOf("@"));
                    } else if (channel.startsWith("/channel/")) {
                        channel = channel.substring(channel.indexOf("/channel/") + 9);
                    } else {
                        client.log("channel信息格式错误: " + channel);
                        continue;
                    }
                    List<Element> link = item.findElementsByCssSelector("a#video-title-link[title], h3[title] > a[aria-label]");
                    if (link.isEmpty()) {
                        client.log("无link信息");
                        continue;
                    }
                    List<Element> time = item.findElementsByCssSelector("#time-status > span, yt-thumbnail-badge-view-model div.ytBadgeShapeText");
                    if (time.isEmpty()) {
                        client.log("无时长信息-元素缺失");
                        continue;
                    }
                    long duration = YoutubeTools.parseDuration(time.getFirst().textContent().trim());
                    if (duration <= 0) {
                        client.log("无时长信息-格式错误");
                        continue;
                    }
                    String url = link.getFirst().attributes().get("href").trim();
                    String title;
                    if (link.getFirst().hasAttribute("title")) {
                        title = link.getFirst().attributes().get("title").trim();
                    } else {
                        title = link.getFirst().attributes().get("aria-label").trim();
                    }
                    String vid = url.substring(url.indexOf("v=") + 2).trim();
                    if (vid.contains("&")) {
                        vid = vid.substring(0, vid.indexOf("&"));
                    }
                    // 格式化信息
                    JSONObject video = new JSONObject();
                    video.fluentPut("id", vid)
                            .fluentPut("title", title)
                            .fluentPut("channel", channel)
                            .fluentPut("duration", duration);
                    client.log(String.format("[EXPOSURE] | %s", JSON.toJSONString(video)));
                    // 所有看到的视频都保存
                    viewableVideoIds.put(vid, video);
                } catch (Exception e) {
                    client.log("视频元素解析失败：" + SystemTool.getStackTrace(e));
                }
            }
        } catch (Exception e) {
            client.log(SystemTool.getStackTrace(e));
        }
        return viewableVideoIds;
    }

    public static void viewVideo(BrowseClient client, Browser browser, String videoId, long videoDuration) throws Exception {
        viewVideo(client, browser, videoId, videoDuration, "");
    }

    /**
     *
     * @param tag 为了双浏览器对比运行设置的模式
     */
    public static void viewVideo(BrowseClient client, Browser browser, String videoId, long videoDuration, String tag) throws Exception {
        // 当前页面中定位目标视频
        browser.navigation().loadUrlAndWait("https://youtube.com/watch?v=" + videoId + "&gl=US&hl=en", Duration.ofSeconds(30));
        Thread.sleep(500);
        Document doc = browser.mainFrame().flatMap(Frame::document).orElse(null);
        if (doc == null) {
            throw new Exception(tag + "DOM处理失败-VIEW");
        }
        // 加入到已观看视频中，并保存
        // client.status.viewedVideos.add(videoId);
        // client.saveStatus();
        // 跳过广告，广告按键无法通过javascript进行点击，必须鼠标移上去
        int tryNum = client.conf.maxPlayDuration * 1000 / 100;
        long currDuration = 0;
        boolean skipped = false;
        while (tryNum-- > 0) {
            // 时长监测
            Optional<Element> durationElement = doc.findElementByCssSelector(".ytp-time-contents > .ytp-time-duration");
            if (durationElement.isPresent()) {
                long duration = YoutubeTools.parseDuration(durationElement.get().innerText().trim());
                if (duration != currDuration) {
                    currDuration = duration;
                    client.log(String.format("%s当前内容长度: %d VS %d", tag, currDuration, videoDuration));
                }
                if (Math.abs(videoDuration - duration) <= 2) {
                    // 只有当没有广告条，并且存在视频时长，且时长与记录的时长相等时，才能进入阅读
                    skipped = true;
                    break;
                }
            }
            // 跳过按键
            for (int i = 0; i < 10; i++) {
                Optional<Element> skipBtn = doc.findElementByCssSelector(".ytp-skip-ad-button, .ytp-ad-skip-button");
                if (skipBtn.isEmpty()) {
                    break;
                }
                skipBtn.get().click();
                Thread.sleep(100);
            }
            Thread.sleep(1000);
        }
        if (!skipped) {
            throw new Exception(tag + "无法进入视频");
        }
        // 开始播放
        client.log(tag + "正式开始播放");
        while (doc.findElementByCssSelector(".ytp-left-controls button.ytp-play-button.ytp-button[data-title-no-tooltip]").isEmpty()) {
            //noinspection BusyWait
            Thread.sleep(500);
        }
        Thread.sleep(1000);
        if (doc.findElementByCssSelector(".ytp-left-controls button.ytp-play-button.ytp-button[data-title-no-tooltip='Play']").isPresent()) {
            // 等带点击完毕
            client.log(tag + "等待真实开播");
            // 首先，使用空格键进行启动播放
            char character = ' ';
            KeyCode keyCode = KeyCode.KEY_CODE_SPACE;
            KeyPressed keyPressed = KeyPressed.newBuilder(keyCode)
                    .keyChar(character)
                    .build();
            KeyTyped keyTyped = KeyTyped.newBuilder(keyCode)
                    .keyChar(character)
                    .build();
            KeyReleased keyReleased = KeyReleased.newBuilder(keyCode)
                    .build();
            browser.dispatch(keyPressed);
            browser.dispatch(keyTyped);
            browser.dispatch(keyReleased);
            Thread.sleep(1000);
            doc = browser.mainFrame().flatMap(Frame::document).orElse(doc);
            // 第二，使用静音+自动播放
            if (doc.findElementByCssSelector(".ytp-left-controls button.ytp-play-button.ytp-button[data-title-no-tooltip='Play']").isPresent()) {
                browser.mainFrame().ifPresent(frame -> frame.executeJavaScript("""
                        // 播放按钮
                        const video = document.querySelector('video');
                        if (video) {
                            video.play()
                                .then(() => {
                                    console.log("播放成功");
                                    video.muted = false; // 播放后取消静音
                                })
                                .catch(err => {
                                    console.error("错误:", err);
                                    // 尝试静音播放
                                    video.muted = !video.muted;
                                    video.muted = true;
                                    video.play().catch(e => console.error("静音播放也失败:", e));
                                });
                        }
                    """));
                Thread.sleep(1000);
            }
            // 第三，使用addTask进行播放，基本不用，需要界面可见
            doc = browser.mainFrame().flatMap(Frame::document).orElse(doc);
            int count = 0;
            while (doc.findElementByCssSelector(".ytp-left-controls button.ytp-play-button.ytp-button[data-title-no-tooltip='Play']").isPresent() && count < 10) {
                client.log("播放开播...");
                count++;
                //noinspection BusyWait
                Thread.sleep(500);
            }
            if (count >= 10) {
                client.log("播放失败，依然等待");
            }
        }

        // 检查时间
        Optional<Element> currentElement = doc.findElementByCssSelector(".ytp-time-contents > .ytp-time-current");
        if (currentElement.isPresent()) {
            double current = YoutubeTools.parseDuration(currentElement.get().innerText().trim());
            client.log(String.format("%s视频时长: %d / %d 秒", tag, (long) current, videoDuration));
            long duration80 = (long) ((videoDuration - current) * 0.8);
            long maxLength = (long) (client.conf.maxPlayDuration * (1 + rand.nextDouble() * 0.2 - 0.1));
            long watchLength = Math.min(duration80, maxLength);
            client.log(String.format("%s观看时长: %d秒", tag, watchLength));
            Thread.sleep(watchLength * 1000);
            // 结束后通过进度条设置到80%以上
            if (duration80 > maxLength) {
                try {
                    browser.mainFrame().ifPresent(frame -> frame.executeJavaScript("""
                                // 播放按钮
                                const video = document.querySelector('video');
                                if (video) {
                                    video.currentTime = video.duration * 0.81;
                                }
                            """));
                    Thread.sleep(10 * 1000);
                } catch (Exception e) {
                    client.log("进度调整失败");
                }
            }
        }
    }

    /**
     * 内部静态类，表示视频的详细信息，包括 snippet 和 statistics。
     */
    public static class Video {
        public String id;

        public Snippet snippet;

        public Statistics statistics;

        /**
         * 内部静态类，表示视频的 snippet 信息，包括标题、描述等。
         */
        public static class Snippet {
            public String channelId;

            public String categoryId;

            public String channelTitle;

            public String description;

            public String title;

            public String publishedAt;

            public List<String> tags; // 添加标签字段
        }

        /**
         * 内部静态类，表示视频的统计信息，包括评论数、喜欢数等。
         */
        public static class Statistics {
            public String commentCount;

            public String favoriteCount;

            public String likeCount;

            public String viewCount;
        }
    }
}
package com.socimata.experiment.youtube;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.socimata.experiment.*;
import com.teamdev.jxbrowser.dom.Document;
import com.teamdev.jxbrowser.dom.Element;
import com.teamdev.jxbrowser.frame.Frame;
import com.teamdev.jxbrowser.ui.Rect;
import top.socialbot.tools.SystemTool;

import java.awt.*;
import java.time.Duration;
import java.time.LocalTime;
import java.time.ZoneId;
import java.util.List;
import java.util.*;

@SuppressWarnings("BusyWait")
public class YouTubeBiasClient extends SingleBrowseClient {
    private final BiasBrowseConfiguration conf = (BiasBrowseConfiguration) super.conf;

    public YouTubeBiasClient(BiasBrowseConfiguration conf) throws Exception {
        super(conf);
        if (!status.appendix.containsKey("exposedBiasVideos")) {
            status.appendix.put("exposedBiasVideos", new JSONArray());
        }
        if (!status.appendix.containsKey("viewedVideos")) {
            status.appendix.put("viewedVideos", new JSONArray());
        }
    }

    @Override
    public void run() {
        Random rand = new Random(new Date().getTime());

        // 是否完成初始化
        if (status.initialized < conf.initContents.size()) {
            log("需要进行初始化");
            for (int i = status.initialized; i < conf.initContents.size(); i++) {
                try {
                    log(String.format(">>>>> 初始化: 第%d个视频", i + 1));
                    // browser.navigation().loadUrlAndWait("https://youtube.com/watch?v=" + conf.initVideos.get(i).id, Duration.ofSeconds(30));
                    BrowseConfiguration.VideoRecord content = conf.initContents.get(i);
                    if (conf.biasCategories.contains(content.category)) {
                        status.appendix.getJSONArray("exposedBiasVideos").add(content);
                    }
                    YoutubeTools.viewVideo(
                            this,
                            browserPanel.browser,
                            content.id,
                            content.duration);
                    status.appendix.getJSONArray("viewedVideos").add(content.id);
                    Thread.sleep(10 * 1000L);
                } catch (Exception e) {
                    log(SystemTool.getStackTrace(e));
                } finally {
                    status.initialized++;
                    saveStatus();
                }
            }
        }

        // 确定随机和偏好阅读的轮次
        conf.biasLevel = Math.max(Math.min(conf.biasLevel, 1.0), 0.0); // 确定强度的合法性
        boolean[] isBiasRound = new boolean[conf.iterations];
        double nextBiasStep = 0.0;
        for (int i = 0; i < conf.iterations; i++) {
            if (conf.biasLevel > 0 && i == (int) nextBiasStep) {
                isBiasRound[i] = true;
                nextBiasStep += 1 / conf.biasLevel;
            } else {
                isBiasRound[i] = false;
            }
        }

        // 单步内循环
        int errCount = 0;
        for (int step = status.step; step < conf.iterations; step++) {
            if (stopping) {
                break;
            }
            lastActiveTime = new Date();
            progress = (int) (100.0 * (step + 1) / conf.iterations);
            try {
                // 测试网络
                log("测试并等待网络连通......");
                waiting = true;
                while (!YoutubeTools.isNetworkAvailable(conf.proxyAddr, conf.proxyPort)) {
                    Thread.sleep(1000);
                }
                waiting = false;

                // 最多刷新3次，使得可读视频数量不为0
                Map<String, JSONObject> viewableVideoIds = new HashMap<>();
                for (int r = 0; r < 3; r++) {
                    // 进入/刷新主页
                    log(String.format("[START] | level (%.2f) - step %03d", conf.biasLevel, step));
                    browserPanel.browser.navigation().loadUrlAndWait("https://www.youtube.com/?gl=US&hl=en", Duration.ofSeconds(30));

                    // 偏好阅读概率
                    log(String.format("本次进行%s阅读", !isBiasRound[step] ? "随机" : "偏好"));

                    // 选择可以观看的地址，记录所有曝光内容
                    Document doc = browserPanel.browser.mainFrame().flatMap(Frame::document).orElse(null);
                    if (doc == null) {
                        continue;
                    }

                    // 等待加载元素
                    log("获取曝光视频");
                    viewableVideoIds = YoutubeTools.extractVideos(this, doc);
                    log(String.format("[F0]总曝光视频数 = %d", viewableVideoIds.size()));

                    log("过滤STEP0：去除重复观看");
                    Map<String, JSONObject> temp = new HashMap<>();
                    for (String vid : viewableVideoIds.keySet()) {
                        if (!status.appendix.getJSONArray("viewedVideos").contains(vid)) {
                            temp.put(vid, viewableVideoIds.get(vid));
                        }
                    }
                    viewableVideoIds = temp;
                    log(String.format("[F1]非重复视频数 = %d", viewableVideoIds.size()));
                    if (viewableVideoIds.isEmpty()) {
                        continue;
                    }

                    // 使用YouTube API检查视频类型
                    log("获取视频类型");
                    Map<String, Integer> vcs = new HashMap<>();
                    for (int j = 0; j < 3; j++) {
                        try {
                            vcs = YoutubeTools.getCategoryId(new ArrayList<>(viewableVideoIds.keySet()), conf.proxyAddr, conf.proxyPort);
                            break;
                        } catch (Exception e) {
                            log(SystemTool.getStackTrace(e));
                        }
                    }
                    log(String.format("[CATEGORY] | %s", JSON.toJSONString(vcs)));

                    log("过滤STEP1：来源白名单可读性");
                    temp = new HashMap<>();
                    for (String vid : viewableVideoIds.keySet()) {
                        // 过滤STEP1：来源白名单可读性
                        JSONObject video = viewableVideoIds.get(vid);
                        boolean contained = false;
                        for (String white : conf.biasSources) {
                            if (white.equalsIgnoreCase(video.getString("channel"))) {
                                contained = true;
                                break;
                            }
                        }
                        boolean isLegal = !isBiasRound[step] || conf.biasSources.isEmpty() || contained;
                        if (isLegal) {
                            temp.put(vid, video);
                        }
                    }
                    viewableVideoIds = temp;
                    log(String.format("[F2]来源合法视频数 = %d", viewableVideoIds.size()));
                    if (viewableVideoIds.isEmpty()) {
                        continue;
                    }

                    // 记录曝光的偏好内容
                    log("记录偏好视频，用于后续可能的重复观看");
                    for (String vid : viewableVideoIds.keySet()) {
                        if (conf.biasCategories.contains(vcs.get(vid))) {
                            viewableVideoIds.get(vid).put("category", vcs.get(vid));
                            status.appendix.getJSONArray("exposedBiasVideos").add(viewableVideoIds.get(vid));
                        }
                    }
                    saveStatus();

                    // 按类型过滤出可看视频
                    log("过滤STEP2：类型可读性");
                    // 偏好阅读，考虑新引入的biasCategoriesWeight变量按分类权重阅读
                    List<Integer> candidateBiasCategories = new ArrayList<>();
                    if (isBiasRound[step]) {
                        int c = SystemTool.getDiscreteRandom(conf.biasCategories, conf.biasCategoriesWeight);
                        candidateBiasCategories.add(c);
                    } else {
                        candidateBiasCategories.addAll(conf.biasCategories); // TODO 非偏好阅读，这个变量的值没有作用
                    }
                    log("候选类型包括：" + JSON.toJSONString(candidateBiasCategories));
                    temp = new HashMap<>();
                    for (String vid : viewableVideoIds.keySet()) {
                        int c = vcs.getOrDefault(vid, -1);
                        boolean isLegal = conf.validCategories.contains(c) && (!isBiasRound[step] || candidateBiasCategories.contains(c));
                        if (isLegal) {
                            temp.put(vid, viewableVideoIds.get(vid));
                        }
                    }
                    viewableVideoIds = temp;
                    log(String.format("[F3]分类合法视频数 = %d", viewableVideoIds.size()));
                    log(String.format("分类合法视频信息：%s", JSON.toJSONString(viewableVideoIds)));
                    if (!viewableVideoIds.isEmpty()) {
                        break;
                    }
                }

                // 如果依然为空，则随机选择一个白名单成员的视频列表进行阅读
                /*
                if (viewableVideoIds.isEmpty() && !conf.biasSources.isEmpty()) {
                    String tgt = conf.biasSources.get(rand.nextInt(conf.biasSources.size()));
                    log(String.format("[CHANNEL] | %s", tgt));
                    browser.navigation().loadUrlAndWait("https://www.youtube.com/" + tgt + "/videos", Duration.ofSeconds(30));
                    Thread.sleep(20 * 1000L);
                    // 选择可以观看的地址，记录所有曝光内容
                    Document doc = browser.mainFrame().flatMap(Frame::document).orElse(null);
                    if (doc != null) {
                        List<Element> items = doc.findElementsByCssSelector("div#contents div#content");
                        for (Element item : items) {
                            Optional<Element> timeEle = item.findElementByCssSelector("div#time-status span[aria-label]");
                            Optional<Element> titleEle = item.findElementByCssSelector("a#video-title-link[aria-label]");
                            if (timeEle.isPresent() && titleEle.isPresent()) {
                                String title = "";
                                String href = "";
                                String vid = "";
                                long duration = -1;
                                try {
                                    title = titleEle.get().innerText().trim();
                                    href = titleEle.get().attributeValue("href").trim();
                                    vid = href.substring(href.indexOf("v=") + 2).trim();
                                    vid = vid.substring(0, vid.contains("&") ? vid.indexOf("&") : vid.length());
                                    duration = duration(timeEle.get().innerText().trim());
                                    viewableVideoIds.add(vid);
                                    durations.put(vid, duration);
                                } catch (Exception e) {
                                    continue;
                                }
                                // 记录
                                Map<String, Object> record = new HashMap<>();
                                record.put("id", vid);
                                record.put("title", title);
                                record.put("channel", tgt);
                                record.put("duration", String.valueOf(duration));
                                log(String.format("[PICKED] | %s", JSON.toJSONString(record)));
                            }
                            break;
                        }
                    }
                }
                */

                // 在历史偏好记录里寻找视频
                if (viewableVideoIds.isEmpty() && isBiasRound[step]) {
                    JSONArray vs = status.appendix.getJSONArray("exposedBiasVideos");
                    log(String.format("无可看视频，从历史曝光和阅读中观看，备选数量：%d", vs.size()));
                    for (int i = 0; i < vs.size(); i++) {
                        viewableVideoIds.put(vs.getJSONObject(i).getString("id"), vs.getJSONObject(i));
                    }
                }

                // 阅读第一个可读的
                if (!viewableVideoIds.isEmpty()) {
                    List<String> videoIds = new ArrayList<>(viewableVideoIds.keySet());
                    Collections.shuffle(videoIds);
                    JSONObject video = viewableVideoIds.get(videoIds.getFirst());
                    // 观看
                    log(String.format("[SELECT] | %s", video));
                    // 保存进度
                    status.step = step + 1;
                    status.appendix.getJSONArray("viewedVideos").add(video.getString("id"));
                    saveStatus();
                    // 只要开始看了，就算看过了，所以这里加一个try避免失败导致整体失效，而且已经提前保存了进度
                    try {
                        YoutubeTools.viewVideo(
                                this,
                                browserPanel.browser,
                                video.getString("id"),
                                video.getIntValue("duration"));
                    } catch (Exception e) {
                        log(SystemTool.getStackTrace(e));
                        // break; // DEBUG
                        status.exception++;
                    } finally {
                        saveStatus();
                        browserPanel.browser.navigation().loadUrlAndWait("about:blank", Duration.ofSeconds(30));
                    }
                } else {
                    throw new Exception("可读视频数量为0");
                }

                errCount = 0;
                // 是否停止
                if (stopping) {
                    break;
                }

                // 是否在睡眠时间
                log("是否睡眠");
                LocalTime localTime = new Date().toInstant().atZone(ZoneId.of("America/New_York")).toLocalTime();
                while (conf.sleepingTiming.contains(localTime.getHour())) {
                    //noinspection BusyWait
                    Thread.sleep(1000L);
                }
                if (stopping) {
                    break;
                }
            } catch (Exception e) {
                log(SystemTool.getStackTrace(e));
                // 状态记录
                step--;
                status.exception++;
                // 有错误也写入状态
                saveStatus();
                // 错误计数
                errCount++;
                if (errCount >= 3) {
                    try {
                        int ms = (errCount / 3) * 15;
                        log(String.format("错误长等待: %d分钟", ms));
                        Thread.sleep(ms * 60 * 1000L);
                    } catch (InterruptedException ex) {
                        throw new RuntimeException(ex);
                    }
                }
                if (stopping) {
                    break;
                }
            } finally {
                // 时间等待一个幂律分布时长
                double q = rand.nextDouble();
                int i;
                for (i = 0; i < dist.length; i++) {
                    if (dist[i] >= q) {
                        break;
                    }
                }
                log(String.format("随机间隔: %d分钟", i));
                try {
                    Thread.sleep(i * 60 * 1000L);
                } catch (InterruptedException e) {
                    //
                }
            }
        }

        stopped = true;
        stopping = false;
        startButton.setEnabled(true);
        stopButton.setEnabled(false);
    }



    @Override
    public Point getClickLocation() {
        Optional<Element> btn = browserPanel.browser.mainFrame().flatMap(Frame::document).flatMap(doc -> doc.findElementByCssSelector(".ytp-left-controls button.ytp-play-button.ytp-button[data-title-no-tooltip='Play']"));
        if (btn.isPresent()) {
            btn.get().scrollIntoView(Element.AlignTo.BOTTOM);
            try {
                Thread.sleep(300);
            } catch (InterruptedException e) {
                throw new RuntimeException(e);
            }
            Rect rect = btn.get().boundingClientRect();
            Point p = browserPanel.browserView.getLocationOnScreen();
            int x = p.x + rect.x() + rect.width() / 2;
            int y = p.y + rect.y() + rect.height() / 2;
            return new Point(x, y);
        } else {
            return null;
        }
    }
}

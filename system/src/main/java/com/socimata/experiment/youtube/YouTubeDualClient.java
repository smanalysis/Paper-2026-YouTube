package com.socimata.experiment.youtube;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.google.common.collect.Sets;
import com.socimata.experiment.*;
import com.teamdev.jxbrowser.dom.Document;
import com.teamdev.jxbrowser.frame.Frame;
import top.socialbot.tools.SystemTool;

import java.awt.*;
import java.time.Duration;
import java.time.LocalTime;
import java.time.ZoneId;
import java.util.*;
import java.util.List;

public class YouTubeDualClient extends DualBrowseClient {

    public YouTubeDualClient(DualBrowseConfiguration conf) throws Exception {
        super(conf);
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
                    BrowseConfiguration.VideoRecord content = conf.initContents.get(i);
                    Thread t0 = new Thread(() -> {
                        try {
                            YoutubeTools.viewVideo(
                                    this,
                                    masterBrowserPanel.browser,
                                    content.id,
                                    content.duration,
                                    "MASTER-");
                        } catch (Exception e) {
                            log(SystemTool.getStackTrace(e));
                        }
                    });
                    Thread t1 = new Thread(() -> {
                        try {
                            YoutubeTools.viewVideo(
                                    this,
                                    servantBrowserPanel.browser,
                                    content.id,
                                    content.duration,
                                    "SERVANT-");
                        } catch (Exception e) {
                            log(SystemTool.getStackTrace(e));
                        }
                    });
                    t0.start();
                    t1.start();
                    t0.join();
                    t1.join();
                    // status.appendix.getJSONArray("viewedVideos").add(content.getString("id"));
                    //noinspection BusyWait
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
        conf.couplingRatio = Math.max(Math.min(conf.couplingRatio, 1.0), 0.0); // 确定强度的合法性
        boolean[] isCouplingRound = new boolean[conf.iterations];
        double nextCouplingStep = 0.0;
        for (int i = 0; i < conf.iterations; i++) {
            if (conf.couplingRatio > 0 && i == (int) nextCouplingStep) {
                isCouplingRound[i] = true;
                nextCouplingStep += 1 / conf.couplingRatio;
            } else {
                isCouplingRound[i] = false;
            }
        }

        // 均匀分布注入视频到各个步骤中
        int[] isInjectingRound = new int[conf.iterations]; // 0代表无注入，大于0的值j，代表注入j-1的视频观看
        for (int i = 0, j = 1, err = 0; i < conf.iterations && j <= conf.injectants.size(); i++) {
            err += conf.injectants.size();
            if (err >= conf.iterations) {
                isInjectingRound[i] = j++;
                err -= conf.iterations;
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
                    //noinspection BusyWait
                    Thread.sleep(1000);
                }
                waiting = false;

                // 本轮信息
                log(String.format("[START] | level (%.2f) - step %03d", conf.couplingRatio, step));
                log(String.format("本次进行%s阅读", isCouplingRound[step] ? "耦合" : "自由"));

                // 刷新列表直至满足要求
                Map<String, JSONObject> masterVideos = new HashMap<>();
                Map<String, JSONObject> servantVideos = new HashMap<>();
                Set<String> intersection = new HashSet<>();
                for (int i = 0, r = 3; i < (isCouplingRound[step] ? 5 : 1) && r > 0; i++, r--) {
                    try {
                        parseValidVideos(masterVideos, servantVideos, isCouplingRound[step]); // 耦合步骤，需要考虑channel的合法性
                        intersection = Sets.intersection(masterVideos.keySet(), servantVideos.keySet());
                    } catch (Exception e) {
                        log("获取视频失败：" + SystemTool.getStackTrace(e));
                        i--; // r并不减，也就是错误重试只有3次
                        status.exception++;
                        continue;
                    }
                    if (!isCouplingRound[step]) {
                        // 非耦合步骤，只要两者都刷新出视频，即可结束
                        if (masterVideos.isEmpty() || servantVideos.isEmpty()) {
                            i--; // r并不减，也就是错误重试只有3次
                            status.exception++;
                        } else {
                            break;
                        }
                    } else {
                        // 耦合环节，如果出现共同视频，且类型符合合法阅读集合，即可结束
                        if (!intersection.isEmpty()) {
                            break;
                        }
                    }
                }
                log(String.format("MASTER合法曝光数量：%s", masterVideos.size()));
                log(String.format("SERVANT合法曝光数量：%s", servantVideos.size()));
                log(String.format("交集大小：%s", intersection.size()));
                log(String.format("[EXPOSURE-MASTER] | %s]", JSON.toJSONString(masterVideos)));
                log(String.format("[EXPOSURE-SERVANT] | %s]", JSON.toJSONString(servantVideos)));
                log(String.format("[INTERSECTION] | %s]", JSON.toJSONString(intersection)));

                // 决定阅读的id
                String masterId, servantId;
                if (isCouplingRound[step]) {
                    // 耦合阅读
                    if (intersection.isEmpty()) {
                        // 但没有共同的视频，挑选master中的一个作为共同阅读
                        log("耦合浏览，但无共同曝光");
                        masterId = new ArrayList<>(masterVideos.keySet()).get(rand.nextInt(masterVideos.size()));
                        servantId = masterId;
                    } else {
                        // 在交集中选取
                        log("耦合浏览");
                        masterId = new ArrayList<>(intersection).get(rand.nextInt(intersection.size()));
                        servantId = masterId;
                    }
                } else {
                    // 去掉交集选择
                    log("差异浏览");
                    List<String> mul = new ArrayList<>(Sets.difference(masterVideos.keySet(), intersection));
                    List<String> sul = new ArrayList<>(Sets.difference(servantVideos.keySet(), intersection));
                    masterId = mul.get(rand.nextInt(mul.size()));
                    servantId = sul.get(rand.nextInt(sul.size()));
                }
                JSONObject masterSelected = masterVideos.get(masterId);
                JSONObject servantSelected = servantVideos.getOrDefault(servantId, masterSelected);
                log(String.format("[SELECT-MASTER] | %s",masterSelected));
                log(String.format("[SELECT-SERVANT] | %s", servantSelected));

                // 观看
                Thread t0 = new Thread(() -> {
                    try {
                        YoutubeTools.viewVideo(
                                this,
                                masterBrowserPanel.browser,
                                masterId,
                                masterSelected.getIntValue("duration"),
                                "MASTER-");
                    } catch (Exception e) {
                        log("观看错误MASTER：" + SystemTool.getStackTrace(e));
                        status.exception++;
                    } finally {
                        // 结束
                        masterBrowserPanel.browser.navigation().loadUrlAndWait("https://www.youtube.com/?gl=US&hl=en", Duration.ofSeconds(30));
                    }
                });
                Thread t1 = new Thread(() -> {
                    try {
                        YoutubeTools.viewVideo(
                                this,
                                servantBrowserPanel.browser,
                                servantId,
                                servantSelected.getIntValue("duration"),
                                "SERVANT-");
                    } catch (Exception e) {
                        log("观看错误SERVANT：" + SystemTool.getStackTrace(e));
                        status.exception++;
                    } finally {
                        // 结束
                        servantBrowserPanel.browser.navigation().loadUrlAndWait("https://www.youtube.com/?gl=US&hl=en", Duration.ofSeconds(30));
                    }
                });
                t0.start();
                t1.start();
                t0.join();
                t1.join();

                // 额外注入观看
                if (isInjectingRound[step] > 0) {
                    try {
                        log(String.format(">>>>> 注入视频：%d", isInjectingRound[step]));
                        BrowseConfiguration.VideoRecord content = conf.injectants.get(isInjectingRound[step] - 1);
                        List<String> candidates = new ArrayList<>();
                        for (String vid : masterVideos.keySet()) {
                            if (masterVideos.get(vid).getIntValue("category") == content.category) {
                                candidates.add(vid);
                            }
                        }
                        if (!candidates.isEmpty()) {
                            int s = rand.nextInt(candidates.size());
                            Thread j0 = new Thread(() -> {
                                try {
                                    YoutubeTools.viewVideo(
                                            this,
                                            masterBrowserPanel.browser,
                                            candidates.get(s),
                                            masterVideos.get(candidates.get(s)).getIntValue("duration"),
                                            "MASTER-INJECT-A-");
                                } catch (Exception e) {
                                    log(SystemTool.getStackTrace(e));
                                }
                            });
                            j0.start();
                            j0.join();
                        } else {
                            Thread j0 = new Thread(() -> {
                                try {
                                    YoutubeTools.viewVideo(
                                            this,
                                            masterBrowserPanel.browser,
                                            content.id,
                                            content.duration,
                                            "MASTER-INJECT-D-");
                                } catch (Exception e) {
                                    log(SystemTool.getStackTrace(e));
                                }
                            });
                            j0.start();
                            j0.join();
                        }
                        //noinspection BusyWait
                        Thread.sleep(10 * 1000L);
                    } catch (Exception e) {
                        log(SystemTool.getStackTrace(e));
                    }
                }

                // 保存进度
                status.step = step + 1;
                saveStatus();
                masterBrowserPanel.browser.navigation().loadUrlAndWait("about:blank", Duration.ofSeconds(30));
                servantBrowserPanel.browser.navigation().loadUrlAndWait("about:blank", Duration.ofSeconds(30));
                errCount = 0;
                // 是否停止
                if (stopping) {
                    break;
                }

                // 是否在睡眠时间
                log("是否睡眠 ...");
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
                // step--; 只有执行完成，才会加1，所以不用减
                status.exception++;
                // 有错误也写入状态
                saveStatus();
                // 错误计数
                errCount++;
                if (errCount >= 3) {
                    try {
                        int ms = (errCount / 3) * 15;
                        log(String.format("错误长等待: %d分钟", ms));
                        //noinspection BusyWait
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
                    //noinspection BusyWait
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

    private void parseValidVideos(Map<String, JSONObject> masterVideos, Map<String, JSONObject> servantVideos, boolean matchChannel) throws Exception {
        // 刷新列表
        log("刷新双方列表");
        Thread t0 = new Thread(() -> {
            masterBrowserPanel.browser.navigation().loadUrlAndWait("https://www.youtube.com/?gl=US&hl=en", Duration.ofSeconds(30));
        });
        Thread t1 = new Thread(() -> {
            servantBrowserPanel.browser.navigation().loadUrlAndWait("https://www.youtube.com/?gl=US&hl=en", Duration.ofSeconds(30));
        });
        t0.start();
        t1.start();
        t0.join();
        t1.join();
        log("刷新结束");

        // 解析文档，获取分类
        Document masterDoc = masterBrowserPanel.browser.mainFrame().flatMap(Frame::document).orElse(null);
        Document servantDoc = servantBrowserPanel.browser.mainFrame().flatMap(Frame::document).orElse(null);
        Map<String, JSONObject> videos1 = new HashMap<>();
        if (masterDoc != null) {
            log("========= MASTER列表内容提取 =========");
            videos1 = YoutubeTools.extractVideos(this, masterDoc);
        }
        Map<String, JSONObject> videos2 = new HashMap<>();
        if (servantDoc != null) {
            log("========= SERVANT列表内容提取 =========");
            videos2 = YoutubeTools.extractVideos(this, servantDoc);
        }
        List<String> ids = new ArrayList<>();
        ids.addAll(videos1.keySet());
        ids.addAll(videos2.keySet());
        Map<String, Integer> categories = YoutubeTools.getCategoryId(ids, conf.proxyAddr, conf.proxyPort);
        log(String.format("[CATEGORY] | %s", JSON.toJSONString(categories)));
        for (String id : videos1.keySet()) {
            int c = categories.getOrDefault(id, -1);
            if ((conf.validCategories.isEmpty() || conf.validCategories.contains(c)) &&
                    (!matchChannel || conf.whiteChannels.isEmpty() || conf.whiteChannels.contains(videos1.get(id).getString("channel").toLowerCase()))) {
                videos1.get(id).put("category", c);
                masterVideos.put(id, videos1.get(id));
            }
        }
        for (String id : videos2.keySet()) {
            int c = categories.getOrDefault(id, -1);
            if ((conf.validCategories.isEmpty() || conf.validCategories.contains(c)) &&
                    (!matchChannel || conf.whiteChannels.isEmpty() || conf.whiteChannels.contains(videos2.get(id).getString("channel").toLowerCase()))) {
                videos2.get(id).put("category", c);
                servantVideos.put(id, videos2.get(id));
            }
        }
    }

    @Override
    public Point getClickLocation() {
        return null;
    }
}

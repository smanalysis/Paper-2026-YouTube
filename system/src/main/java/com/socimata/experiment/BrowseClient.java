package com.socimata.experiment;

import com.alibaba.fastjson2.JSON;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import top.socialbot.tools.SystemTool;

import javax.swing.*;
import java.awt.*;
import java.io.File;
import java.io.FileInputStream;
import java.nio.file.Files;
import java.util.Date;

@SuppressWarnings("BusyWait")
public abstract class BrowseClient extends JPanel implements Runnable {
    public final Logger logger;

    public BrowseConfiguration conf;
    public File statusFile;
    public BrowseStatus status;

    protected final double[] dist = new double[60];

    protected final JTextArea logArea;
    protected final JButton startButton;
    protected final JButton stopButton;

    public boolean dynamicLog = false;
    public boolean stopping = false;
    public boolean stopped = true;
    public boolean waiting = false;

    protected Date lastActiveTime = new Date(0);
    protected int progress = 0;

    public BrowseClient(BrowseConfiguration conf) throws Exception {
        this.conf = conf;
        this.logger = LoggerFactory.getLogger(conf.platform.toUpperCase() + "-" + conf.name);
        this.statusFile = new File(conf.name + ".status.json");
        if (statusFile.exists()) {
            this.status = loadStatus();
        } else {
            this.status = new BrowseStatus();
        }
        this.progress = (int) (100.0 * (status.step + 1) / conf.iterations);
        // 计算等待时间分布
        double all = 0;
        for (int i = 0; i < dist.length; i++) {
            dist[i] = Math.pow(i + 1, -Math.abs(conf.intervalFactor));
            all += dist[i];
        }
        for (int i = 0; i < dist.length; i++) {
            dist[i] = dist[i] / all;
            if (i > 0) {
                dist[i] = dist[i] + dist[i - 1];
            }
        }
        dist[dist.length - 1] = 1.0;
        // 构建界面
        this.setLayout( new BorderLayout());
        // 1. 日志区域
        logArea = new JTextArea();
        logArea.setEditable(false);
        logArea.setLineWrap(false); // 自动换行
        logArea.setWrapStyleWord(true); // 在单词边界换行
        logArea.setFont(new Font("宋体", Font.PLAIN, 12)); // 设置字体
        logArea.setBackground(new Color(240, 240, 240));
        JScrollPane scrollPane = new JScrollPane(logArea);
        scrollPane.setVerticalScrollBarPolicy(JScrollPane.VERTICAL_SCROLLBAR_ALWAYS); // 总是显示垂直滚动条
        scrollPane.setHorizontalScrollBarPolicy(JScrollPane.HORIZONTAL_SCROLLBAR_ALWAYS); // 总是显示水平滚动条
        // 2. 按键区域
        JToolBar toolBar = new JToolBar();
        toolBar.setFloatable(false); // 禁止拖动工具栏
        startButton = new JButton("启动");
        toolBar.add(startButton);
        stopButton = new JButton("停止");
        toolBar.add(stopButton);
        toolBar.addSeparator();
        JButton logButton = new JButton("显示日志");
        toolBar.add(logButton);
        // 按键事件
        startButton.addActionListener(e -> start());
        stopButton.addActionListener(e -> stop());
        logButton.addActionListener(e -> {
            dynamicLog = !dynamicLog;
            logButton.setText(dynamicLog ? "关闭日志" : "显示日志");
            if (dynamicLog) {
                logArea.setText(String.join("\n", status.recentLogs));
            } else {
                logArea.setText("");
            }
        });
        //
        JSplitPane splitPane = new JSplitPane(JSplitPane.VERTICAL_SPLIT, buildCenter(), scrollPane);
        splitPane.setDividerLocation(0.8); // 初始分割线位置
        splitPane.setOneTouchExpandable(true); // 显示快速展开/折叠按钮
        splitPane.setResizeWeight(0.2); // 调整大小时左侧面板的比例变化权重
        splitPane.setDividerSize(10);
        this.setBorder(BorderFactory.createLineBorder(Color.GRAY));
        this.add(toolBar, BorderLayout.NORTH);
        this.add(splitPane, BorderLayout.CENTER);
        this.setPreferredSize(new Dimension(1600, 1080));
    }

    public StatisticTableFrame.TableData getProgressDate() {
        return new StatisticTableFrame.TableData(
                conf.name,
                stopped ? "Stopped" : waiting ? "Waiting" : "Running",
                status.exception,
                lastActiveTime,
                progress
        );
    }

    public void start() {
        if (stopped) {
            new Thread(this).start();
            stopped = false;
            stopping = false;
            startButton.setEnabled(false);
            stopButton.setEnabled(true);
        }
    }

    public void stop() {
        stopping = true;
        stopButton.setEnabled(false);
        new Thread(() -> {
            while (!stopped) {
                try {
                    Thread.sleep(100);
                } catch (InterruptedException e) {
                    throw new RuntimeException(e);
                }
            }
            startButton.setEnabled(true);
        }).start();
    }

    public void log(String msg) {
        logger.warn(msg);
        // 记录最新的300行日志，自行加入时间戳
        if (status.recentLogs.size() > 300) {
            status.recentLogs.removeFirst();
        }
        status.recentLogs.add(new Date() + " | " + msg);
        if (dynamicLog) {
            logArea.setText(String.join("\n", status.recentLogs));
        }
    }

    public void logSilent(String msg) {
        logger.info(msg);
    }

    public BrowseStatus loadStatus() {
        if (statusFile.exists()) {
            try {
                return JSON.parseObject(new FileInputStream(statusFile), BrowseStatus.class);
                // status.recentLogs = new LinkedList<>(status.recentLogs);
                // status.viewedVideos = new LinkedList<>(status.viewedVideos);
                // status.exposedBiasVideos = new LinkedList<>(status.exposedBiasVideos);
            } catch (Exception e) {
                log(SystemTool.getStackTrace(e));
            }
        }
        return null;
    }

    public void saveStatus() {
        try {
            Files.write(statusFile.toPath(), JSON.toJSONString(status).getBytes());
        } catch (Exception e) {
            log(SystemTool.getStackTrace(e));
        }
    }

    /**
     * 打开浏览器
     */
    abstract public JPanel buildCenter();

    abstract public Point getClickLocation();
}

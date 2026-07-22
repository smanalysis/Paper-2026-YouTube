package com.socimata.experiment;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.formdev.flatlaf.FlatLightLaf;
import com.socimata.experiment.bilibili.BilibiliBiasClient;
import com.socimata.experiment.google.GoogleBiasClient;
import com.socimata.experiment.google.GoogleQueryServer;
import com.socimata.experiment.weibo.WeiboBiasClient;
import com.socimata.experiment.youtube.YouTubeBiasClient;
import com.socimata.experiment.youtube.YouTubeDualClient;

import javax.swing.*;
import java.awt.*;
import java.awt.event.InputEvent;
import java.awt.event.MouseEvent;
import java.io.FileInputStream;
import java.util.List;
import java.util.Queue;
import java.util.*;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;

public class MainWin {

    private static boolean isMouseLock = false;
    private static int x, y;

    private static final Lock lock = new ReentrantLock();
    private static final Queue<String> tasks = new LinkedBlockingQueue<>();
    private static final Map<String, BrowseClient> clients = new LinkedHashMap<>();
    private static final JFrame frame = new JFrame("阅读实验");

    private static JList<String> nameList;
    private static boolean canAutoClick = false;

    public static Robot bot;

    static {
        FlatLightLaf.setup();
    }

    public static void addTask(String name) {
        try {
            lock.lock();
            tasks.offer(name);
        } finally {
            lock.unlock();
        }
    }

    public static void main(String[] args) throws Exception {
        JSONArray array = JSON.parseArray(new FileInputStream("browse.conf.json"));
        String[] names = new String[array.size()];
        for (int i = 0; i < array.size(); i++) {
            JSONObject obj = (JSONObject) array.get(i);
            names[i] = obj.getString("name");
            BrowseClient client = switch (obj.getString("platform")) {
                case "YouTube-Bias" -> new YouTubeBiasClient(obj.to(BiasBrowseConfiguration.class));
                case "Google-Bias" -> new GoogleBiasClient(obj.to(BiasBrowseConfiguration.class));
                case "Weibo-Bias" -> new WeiboBiasClient(obj.to(BiasBrowseConfiguration.class));
                case "Bilibili-Bias" -> new BilibiliBiasClient(obj.to(BiasBrowseConfiguration.class));
                case "YouTube-Dual" -> new YouTubeDualClient(obj.to(DualBrowseConfiguration.class));
                default -> throw new Exception("无对应平台客户端");
            };
            clients.put(names[i], client);
        }

        // 元素
        createStringJList(names);
        JScrollPane scrollPane = new JScrollPane(nameList);
        scrollPane.setBorder(BorderFactory.createLineBorder(Color.GRAY));
        JToolBar toolBar = createToolBar();

        // 创建主窗口
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        BorderLayout bl = new BorderLayout();
        bl.setHgap(5);
        bl.setVgap(5);
        JPanel panel = new JPanel(bl);
        panel.add(new Panel(), BorderLayout.CENTER);
        panel.add(toolBar, BorderLayout.NORTH);
        panel.add(scrollPane, BorderLayout.WEST);
        frame.setContentPane(panel);
        frame.setPreferredSize(new Dimension(1600, 1024));
        frame.pack();
        frame.setVisible(true);
        // 添加窗口状态监听器
        /*
        frame.addWindowListener(new WindowAdapter() {
            @Override
            public void windowActivated(WindowEvent e) {
                e.getWindow().setAlwaysOnTop(true);
            }
        });*/

        // 鼠标锁定功能
        bot = new Robot();
        Toolkit.getDefaultToolkit().addAWTEventListener(event -> {
            if (event instanceof MouseEvent me) {
                // System.out.println("全局事件: " + me.getID() + " at " + me.getPoint());
                if (isMouseLock && me.getID() == MouseEvent.MOUSE_MOVED) {
                    bot.mouseMove(x, y);
                }
            }
        }, AWTEvent.MOUSE_MOTION_EVENT_MASK | AWTEvent.MOUSE_EVENT_MASK);

        // 模拟点击线程
        new Thread(() -> {
            while (true) {
                try {
                    lock.lock();
                    // 空队列，则等待
                    if (tasks.isEmpty() || !canAutoClick) {
                        bot.delay(100);
                        continue;
                    }
                    // 非空队列，切换显示
                    String name = tasks.poll();
                    assert name != null;
                    frame.setAlwaysOnTop(true);
                    toggle(name);
                    bot.delay(2000);
                    // 固化鼠标
                    Point p = clients.get(name).getClickLocation();
                    x = p.x;
                    y = p.y;
                    bot.mouseMove(0, 0);
                    bot.delay(300);
                    isMouseLock = true;
                    bot.mouseMove(x, y);
                    bot.delay(500);
                    // 点击
                    bot.delay(100);
                    bot.mousePress(InputEvent.BUTTON1_DOWN_MASK);
                    bot.delay(10);
                    bot.mouseRelease(InputEvent.BUTTON1_DOWN_MASK);
                    bot.delay(100);
                    bot.mouseMove(0, 0);
                } catch (Exception e) {
                    //
                } finally {
                    isMouseLock = false;
                    frame.setAlwaysOnTop(false);
                    lock.unlock();
                    bot.delay(10000);
                }
            }

        }).start();
    }

    private static void createStringJList(String[] names) {
        nameList = new JList<>(names);
        nameList.setSelectionMode(ListSelectionModel.SINGLE_SELECTION); // 单选模式
        nameList.setFixedCellHeight(25); // 设置每行高度
        nameList.setFixedCellWidth(200);
        nameList.setCellRenderer(new DefaultListCellRenderer() {
            @Override
            public Component getListCellRendererComponent(JList<?> list, Object value,
                                                          int index, boolean isSelected, boolean cellHasFocus) {
                super.getListCellRendererComponent(list, value, index, isSelected, cellHasFocus);
                // 奇数行和偶数行不同背景色
                if (index % 2 == 0) {
                    setBackground(isSelected ? Color.BLUE : new Color(240, 240, 240));
                } else {
                    setBackground(isSelected ? Color.BLUE : Color.WHITE);
                }
                // 设置文字颜色
                setForeground(isSelected ? Color.WHITE : Color.BLACK);
                return this;
            }
        });
    }

    static private JToolBar createToolBar() {
        JToolBar toolBar = new JToolBar();
        toolBar.setFloatable(false); // 禁止拖动工具栏
        JButton jumpButton = new JButton("切换");
        toolBar.add(jumpButton);
        JButton hiddenButton = new JButton("隐藏");
        toolBar.add(hiddenButton);

        toolBar.addSeparator();

        JButton startAllButton = new JButton("全部启动");
        toolBar.add(startAllButton);
        JButton stopAllButton = new JButton("全部停止");
        toolBar.add(stopAllButton);

        toolBar.addSeparator();

        JButton pauseClickButton = new JButton("允许点击");
        pauseClickButton.setForeground(new Color(0, 100, 0));
        toolBar.add(pauseClickButton);
        JButton statisticButton = new JButton("统计信息");
        toolBar.add(statisticButton);

        toolBar.addSeparator();

        JButton googleRSSButton = new JButton("GoogleRSS采集");
        toolBar.add(googleRSSButton);

        // 切换
        jumpButton.addActionListener(e -> toggle(nameList.getSelectedValue()));
        hiddenButton.addActionListener(e -> toggle(""));
        // 全部启动
        startAllButton.addActionListener(e -> {
            new Thread(() -> {
                startAllButton.setEnabled(false);
                stopAllButton.setEnabled(false);
                Random rnd = new Random(new Date().getTime());
                for (String name : clients.keySet()) {
                    clients.get(name).start();
                    try {
                        Thread.sleep(rnd.nextInt(30, 91) * 1000L);
                    } catch (InterruptedException ex) {
                        throw new RuntimeException(ex);
                    }
                }
                startAllButton.setEnabled(true);
                stopAllButton.setEnabled(true);
            }).start();
        });
        stopAllButton.addActionListener(e -> {
            for (String name : clients.keySet()) {
                clients.get(name).stop();
            }
        });

        // 模拟点击的启动和关闭
        pauseClickButton.addActionListener(e -> {
            try {
                lock.lock();
                canAutoClick = !canAutoClick;
                if (canAutoClick) {
                    pauseClickButton.setText("禁止点击");
                    pauseClickButton.setForeground(Color.RED);
                    jumpButton.setEnabled(false);
                } else {
                    pauseClickButton.setText("允许点击");
                    pauseClickButton.setForeground(new Color(0, 100, 0));
                    jumpButton.setEnabled(true);
                    // frame.setAlwaysOnTop(false);
                }
            } finally {
                lock.unlock();
            }
        });
        // 统计信息
        statisticButton.addActionListener(e -> {
            // 关闭点击
            canAutoClick = false;
            pauseClickButton.setText("允许点击");
            pauseClickButton.setForeground(new Color(0, 100, 0));
            jumpButton.setEnabled(true);
            // frame.setAlwaysOnTop(false);
            // 显示所有进度信息
            List<StatisticTableFrame.TableData> dataList = new ArrayList<>();
            for (int i = 1; i < nameList.getModel().getSize(); i++) {
                String name = nameList.getModel().getElementAt(i);
                dataList.add(clients.get(name).getProgressDate());
            }
            SwingUtilities.invokeLater(() -> {
                new StatisticTableFrame(dataList).setVisible(true);
            });
        });
        //
        googleRSSButton.addActionListener(e -> {
            //
            String proxy = JOptionPane.showInputDialog(
                    "请输入代理服务器地址，包括地址和端口，冒号分割:",
                    "127.0.0.1:7890"
            );
            try {
                if (proxy != null) {
                    String[] param = proxy.split(":");
                    if (param.length == 2) {
                        new Thread(new GoogleQueryServer(param[0], Integer.parseInt(param[1]))).start();
                        JOptionPane.showMessageDialog(null, "服务器启动");
                        return;
                    }
                }
            } catch (Exception ex) {
                //
            }
            JOptionPane.showMessageDialog(null, "启动失败");
        });



        return toolBar;
    }

    protected static void toggle(String name) {
        Component old = ((BorderLayout) frame.getContentPane().getLayout()).getLayoutComponent(BorderLayout.CENTER);
        if (old != null) {
            frame.getContentPane().remove(old);
        }
        if (name == null || name.isEmpty()) {
            frame.getContentPane().add(new Panel(), BorderLayout.CENTER);
            frame.setTitle("阅读实验");
        } else {
            frame.getContentPane().add(clients.get(name), BorderLayout.CENTER);
            frame.setTitle("阅读实验 - " + name);
        }

        frame.getContentPane().revalidate();
        frame.getContentPane().repaint();
    }
}


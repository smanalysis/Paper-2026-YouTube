package com.socimata.experiment;

import com.teamdev.jxbrowser.browser.Browser;
import com.teamdev.jxbrowser.browser.callback.*;
import com.teamdev.jxbrowser.engine.Engine;
import com.teamdev.jxbrowser.engine.EngineOptions;
import com.teamdev.jxbrowser.engine.Language;
import com.teamdev.jxbrowser.engine.ProprietaryFeature;
import com.teamdev.jxbrowser.frame.Frame;
import com.teamdev.jxbrowser.navigation.event.FrameLoadFailed;
import com.teamdev.jxbrowser.navigation.event.FrameLoadFinished;
import com.teamdev.jxbrowser.net.proxy.CustomProxyConfig;
import com.teamdev.jxbrowser.plugin.callback.AllowPluginCallback;
import com.teamdev.jxbrowser.view.swing.BrowserView;

import javax.swing.*;
import java.awt.*;
import java.nio.file.Path;
import java.text.MessageFormat;
import java.time.Duration;

import static com.teamdev.jxbrowser.engine.RenderingMode.HARDWARE_ACCELERATED;

public class BrowserPanel extends JPanel {
    static {
        // noinspection SpellCheckingInspection
        System.setProperty("jxbrowser.license.key", "");
    }

    public Browser browser;
    public BrowserView browserView;

    public void setProxy(String proxyAddr, int proxyPort) {
        if (proxyAddr != null && !proxyAddr.isBlank()) {
            browser.profile().proxy()
                    .config(CustomProxyConfig.newInstance(
                            MessageFormat.format("http={0}:{1};https={0}:{1};ftp={0}:{1};socks={0}:{1}",
                                    proxyAddr, "" + proxyPort),
                            "<local>"));
        }
    }

    public BrowserPanel(String userDataDir, String proxyAddr, int proxyPort) {
        // 主面板使用GridBagLayout
        JPanel leftNorthPanel = new JPanel(new GridBagLayout());
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.fill = GridBagConstraints.HORIZONTAL;
        gbc.insets = new Insets(1, 1, 1, 1); // 组件间距
        // 文本框（自动扩展）
        gbc.gridx = 0;
        gbc.gridy = 0;
        gbc.weightx = 0.0; // 设置权重使文本框扩展
        gbc.ipady = 0;
        JLabel tagLabel = new JLabel(userDataDir);
        leftNorthPanel.add(tagLabel, gbc);
        // 文本框（自动扩展）
        gbc.gridx = 1;
        gbc.gridy = 0;
        gbc.weightx = 1.0; // 设置权重使文本框扩展
        gbc.ipady = 0;
        JTextField urlField = new JTextField();
        urlField.setText("https://www.google.com/?gl=US&hl=en");
        leftNorthPanel.add(urlField, gbc);
        // 最后一个按键
        gbc.gridx = 2;
        gbc.gridy = 0;
        gbc.weightx = 0.0; // 重置权重
        gbc.ipady = 0;
        JButton goButton = new JButton("跳转");
        leftNorthPanel.add(goButton, gbc);
        // 最后一个按键
        gbc.gridx = 3;
        gbc.gridy = 0;
        gbc.weightx = 0.0; // 重置权重
        gbc.ipady = 0;
        JButton devButton = new JButton("开发");
        leftNorthPanel.add(devButton, gbc);
        // 最后一个按键
        gbc.gridx = 4;
        gbc.gridy = 0;
        gbc.weightx = 0.0; // 重置权重
        gbc.ipady = 0;
        JButton testButton = new JButton("测试");
        leftNorthPanel.add(testButton, gbc);

        // 构建浏览器
        Engine engine = Engine.newInstance(
                EngineOptions.newBuilder(HARDWARE_ACCELERATED)
                        .userDataDir(Path.of("./_chrome/" + userDataDir + "/"))
                        .language(Language.ENGLISH_US)
                        .enableProprietaryFeature(ProprietaryFeature.AAC)
                        .enableProprietaryFeature(ProprietaryFeature.H_264)
                        .enableProprietaryFeature(ProprietaryFeature.HEVC)
                        .build());
        browser = engine.newBrowser();
        setProxy(proxyAddr, proxyPort);
        browser.profile().plugins().set(AllowPluginCallback.class, (params) -> AllowPluginCallback.Response.deny());
        browser.set(AlertCallback.class, (params, tell) -> tell.ok());
        browser.set(ConfirmCallback.class, (params, tell) -> tell.cancel());
        browser.set(PromptCallback.class, (params, tell) -> tell.cancel());
        browser.set(BeforeUnloadCallback.class, (params, tell) -> tell.stay());
        browser.set(CreatePopupCallback.class, params -> CreatePopupCallback.Response.suppress());
        browser.audio().mute();
        browser.resize(1200, 1080);
        browser.userAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36");
        // 添加加载监听器
        browser.navigation().on(FrameLoadFinished.class, event -> {
            Frame frame = event.frame();
            // 只处理主框架的加载完成事件
            if (frame.isMain()) {
                String currentUrl = browser.url();
                SwingUtilities.invokeLater(() -> {
                    urlField.setText(currentUrl);
                });
            }
        });
        browserView = BrowserView.newInstance(browser);

        goButton.addActionListener(e -> browser.navigation().loadUrlAndWait(urlField.getText(), Duration.ofSeconds(10)));
        devButton.addActionListener(e -> browser.devTools().show());
        testButton.addActionListener(e -> {
            /*Point p = browserView.getLocationOnScreen();
            System.out.println(p);
            browser.mainFrame().flatMap(Frame::document).flatMap(doc -> doc.findElementByCssSelector(".ytp-left-controls button[title='Play (k)']")).ifPresent(element -> {
                Rect rect = element.boundingClientRect();
                System.out.println(rect);
                element.scrollIntoView(Element.AlignTo.BOTTOM);
                rect = element.boundingClientRect();
                System.out.println(rect);
                int x = p.x + rect.x() + rect.width() / 2;
                int y = p.y + rect.y() + rect.height() / 2;
                MainWin.bot.mouseMove(x, y);
            });*/
        });

        this.setLayout(new BorderLayout());
        this.add(leftNorthPanel, BorderLayout.NORTH);
        this.add(browserView, BorderLayout.CENTER);
    }

    public static void main(String[] args) {
        JFrame frame = new JFrame();
        frame.getContentPane().add(new BrowserPanel("userDataDir", "", 0), BorderLayout.CENTER);
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        frame.setSize(800, 600);
        frame.setLocationRelativeTo(null);
        frame.setVisible(true);
    }
}

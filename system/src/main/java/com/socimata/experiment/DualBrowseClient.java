package com.socimata.experiment;

import java.util.List;
import javax.swing.*;
import java.awt.*;
import java.util.ArrayList;

public abstract class DualBrowseClient extends BrowseClient implements Runnable {

    protected DualBrowseConfiguration conf = (DualBrowseConfiguration) super.conf;

    protected BrowserPanel masterBrowserPanel;
    protected BrowserPanel servantBrowserPanel;

    public DualBrowseClient(DualBrowseConfiguration conf) throws Exception {
        super(conf);
        //
        servantBrowserPanel.setProxy(this.conf.servantProxyAddr, this.conf.servantProxyPort);
        //
        List<String> channels = new ArrayList<>();
        for (String c : conf.whiteChannels) {
            channels.add(c.toLowerCase());
        }
        conf.whiteChannels = channels;
    }

    /**
     * 打开浏览器
     */
    public JPanel buildCenter() {
        JPanel centerPanel = new JPanel();
        centerPanel.setLayout(new BorderLayout());

        masterBrowserPanel = new BrowserPanel(super.conf.name + "-MASTER", super.conf.proxyAddr, super.conf.proxyPort);
        servantBrowserPanel =  new BrowserPanel(super.conf.name + "-SERVANT", super.conf.proxyAddr, super.conf.proxyPort);

        JSplitPane splitPane = new JSplitPane(JSplitPane.HORIZONTAL_SPLIT, masterBrowserPanel, servantBrowserPanel);
        splitPane.setDividerLocation(650); // 初始分割线位置
        splitPane.setOneTouchExpandable(true); // 显示快速展开/折叠按钮
        splitPane.setResizeWeight(0.2); // 调整大小时左侧面板的比例变化权重
        splitPane.setDividerSize(10);
        centerPanel.add(splitPane, BorderLayout.CENTER);

        return centerPanel;
    }
}

package com.socimata.experiment;

import javax.swing.*;

public abstract class SingleBrowseClient extends BrowseClient implements Runnable {

    protected BrowserPanel browserPanel;

    public SingleBrowseClient(BrowseConfiguration conf) throws Exception {
        super(conf);
    }

    /**
     * 打开浏览器
     */
    public JPanel buildCenter() {
        browserPanel = new BrowserPanel(conf.name, conf.proxyAddr, conf.proxyPort);
        return browserPanel;
    }
}

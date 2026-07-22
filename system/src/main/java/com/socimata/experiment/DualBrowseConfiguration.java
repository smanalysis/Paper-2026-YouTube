package com.socimata.experiment;

import com.alibaba.fastjson2.JSONObject;

import java.util.ArrayList;
import java.util.List;

public class DualBrowseConfiguration extends BrowseConfiguration {

    public double couplingRatio = 0.0;

    public String servantProxyAddr = "";

    public int servantProxyPort = 0;

    /**
     * 均匀分布在全部实验步骤上，Master额外的注入（观看）列表中的视频
     */
    public List<BrowseConfiguration.VideoRecord> injectants = new ArrayList<>();

    public List<String> whiteChannels = new ArrayList<>();
}

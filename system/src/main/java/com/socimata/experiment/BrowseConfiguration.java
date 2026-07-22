package com.socimata.experiment;

import com.alibaba.fastjson2.JSONObject;

import java.util.ArrayList;
import java.util.List;

public class BrowseConfiguration {
    public String platform = "";

    public String name = "";

    public String proxyAddr = "";

    public int proxyPort = 0;

    public List<VideoRecord> initContents = new ArrayList<>();

    public List<Integer> validCategories = new ArrayList<>();

    public List<Integer> sleepingTiming = new ArrayList<>();

    public double intervalFactor = 0.0;

    public int iterations = 300;

    public int maxPlayDuration = 300;

    public static class VideoRecord {
        public int category;

        public String id;

        public int duration;
    }
}



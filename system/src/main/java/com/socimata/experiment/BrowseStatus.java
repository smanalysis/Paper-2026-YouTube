package com.socimata.experiment;


import com.alibaba.fastjson2.JSONObject;
import com.alibaba.fastjson2.annotation.JSONField;

import java.util.LinkedList;
import java.util.List;

public class BrowseStatus {
    @JSONField(ordinal = 1)
    public int initialized = 0;

    @JSONField(ordinal = 2)
    public int step = 0;

    @JSONField(ordinal = 3)
    public int exception = 0;

    @JSONField(ordinal = 4)
    public JSONObject appendix = new JSONObject();

    @JSONField(ordinal = 5)
    public List<String> recentLogs = new LinkedList<>();
}

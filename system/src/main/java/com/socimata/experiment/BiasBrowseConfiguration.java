package com.socimata.experiment;

import java.util.ArrayList;
import java.util.List;

public class BiasBrowseConfiguration extends BrowseConfiguration {

    public double biasLevel = 0.0;

    public List<Integer> biasCategories = new ArrayList<>();

    public List<Double> biasCategoriesWeight = new ArrayList<>();

    public List<String> biasSources = new ArrayList<>();

    public List<String> biasKeywords = new ArrayList<>();
}



package com.socimata.experiment.youtube;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.alibaba.fastjson2.JSONWriter;
import com.socimata.experiment.SingleBrowseClient;
import com.socimata.experiment.BiasBrowseConfiguration;
import com.teamdev.jxbrowser.dom.Document;
import com.teamdev.jxbrowser.dom.Element;
import com.teamdev.jxbrowser.frame.Frame;
import top.socialbot.tools.FileTool;

import java.awt.*;
import java.io.FileInputStream;
import java.text.MessageFormat;
import java.time.Duration;
import java.util.*;
import java.util.List;

public class ChannelInfoCollector {
    public static void toPrompts() throws Exception {
        String template = """
                Please use your existing knowledge base and the information provided to infer the political bias of a YouTube channel.
                The result should be returned the response in JSON object format, containing 3 attributes:
                1. Channel ID, copy the provided id value and store it in the id attribute as a string;
                2. The bias judgment result belongs to one of "Left", "Right" and "Center", stored in the bias attribute as a string;
                3. Give the basis for the judgment, no more than 300 words, stored in the reason attribute as a string.
                Channel Information including:
                Channel ID: {0}
                Channel name: {1}
                Channel introduction: {2}
                List of video titles recently released by the channel:
                """;

        List<String> lines = FileTool.readFileLines("./channel-info.txt");
        List<String> prompts = new ArrayList<>();
        for (String line : lines) {
            JSONObject json = JSON.parseObject(line);
            if (json.containsKey("name") && !json.getString("name").trim().isEmpty()) {
                StringBuilder prompt = new StringBuilder(MessageFormat.format(template,
                        json.getString("channel"),
                        json.getString("name"),
                        json.getString("description")));
                List<String> titles = json.getJSONArray("titles").toJavaList(String.class);
                for (String title : titles) {
                    prompt.append("- ").append(title).append("\n");
                }
                prompts.add(prompt.toString());
                System.out.println(prompt.toString());
            }
        }
        FileTool.writeFile(Collections.singletonList(JSON.toJSONString(prompts, JSONWriter.Feature.PrettyFormat)), "./prompts.txt");
    }

    public static void collect() throws Exception {
        JSONArray array = JSON.parseArray(new FileInputStream("browse.conf.json"));
        List<BiasBrowseConfiguration> confs = array.toJavaList(BiasBrowseConfiguration.class);

        List<String> channels = Arrays.asList("@ForbesBreakingNews", "@Firstpost", "@markets", "@AIJACvideo", "@cnnnews18", "@ListenToTimesRadio", "@TBNIsrael", "@TheWatchmanwithErickStakelbeck", "@wsj", "@BreakThroughNews", "@bulwarkmedia", "@24HNewsOfficial", "@MahyarTousiTV", "@Murraydebates", "@globalnewstw", "@business", "@kcalnews", "@CRUXnews", "@TalkingFeds", "@voachinese", "@BloombergPodcasts", "@JNS_TV", "@JamunaTVbd", "@GBNewsOnline", "@tv7israelnews", "@aljazeera", "@DemocracyDocket", "@neutralitystudies", "@PulsePointReport", "@GeopoliticalEconomyReport", "@NHKWORLDJAPAN", "@SenatorWhitehouse", "@%E5%85%A8%E7%90%83%E5%A4%A7%E8%A6%96%E9%87%8EGlobal_Vision", "@BBCWorldService", "@TaiwanPlusNews", "@katianecrochefioafio6318", "@BloombergTechnology", "@NTDCHINESE", "@WTKR3", "@moreperfectunion", "@NationalConservatism", "@KCRA", "@timesofindia", "@tvbsfocus", "@JavaDiscover", "@NewsNation", "@TheKatieHalperShow", "@ChinaUpdate", "@cbssf", "@chinatruths", "@WYMTTelevision", "@zeenews", "@taiwan_talks", "@VOANews", "@LukeBeasley", "@Douglasmurrayspeaks", "@DawnNewsEnglish", "@TimesofIsrael", "@OracleEyes41", "@tvbschannel", "@NegociosTV", "@CNBC-TV18", "@globalvisiontalk", "@%E9%A0%AD%E6%A2%9D%E9%96%8B%E8%AC%9BHeadlinesTalk", "@CBSChicago", "@HT-Videos", "@Thebasedconservative", "@WFXRNEWS", "@tvbstalk", "@adammockler", "@MurraysInsights", "@abscbnnews", "@CBS19", "@JantaKaReporter", "@TRTWorldNow", "@setinews", "@CBSNewYork", "@RepublicTVBharat", "@dwespanol", "@Wqadnews8", "@ANCalerts", "@RFU", "@Foxweather", "@UATVEnglish", "@fdd", "@UNTVNewsandRescue", "@USS-GLOBAL", "@geopoliticshaiphong", "@SiliconCurtain", "@fox9", "@MaxVelocityWX", "@TheStrategistChannels", "@ANINewsIndia", "@USSpentagonal", "@%E4%B8%AD%E5%A4%A9%E9%9B%BB%E8%A6%96CtiTv", "@ponderingpolitics", "@zeteo_news", "@setnews", "@BBCBangla", "@aljazeeramubasher", "@journeyman", "@chinainsights4458", "@commonwealthclubworldaffairs", "@WSJNews", "@judgingfreedom", "@YanasaTV", "@LUISAANDRADE", "@USreporting", "@carldemaioca", "@WTHR13News", "@SouthChinaMorningPost", "@gmanews", "@TheUSNewscaster", "@YahooFinance", "@WBTWNews13", "@WGRZTVNews", "@newschannel9", "@jsonline", "@halawiyat_taqlidia", "@France24_es", "@LeisRealTalk", "@WRAL5", "@MILSIMUSMCC", "@Infinitycom", "@NATONews", "@ONSCENETV", "@ResisttheMainstream", "@KREM2NewsSpokane", "@Kanal13AZ", "@%E4%B8%AD%E5%A4%A9%E6%96%B0%E8%81%9ECtiNews", "@ActionNewsNow", "@cbssacramento", "@CNBCMakeIt", "@NBCMontana", "@PerunAU", "c/Croch%C3%AAbyRafhaelaMello", "@nationtvTH", "@TVBSNEWS01", "@ORFDelhi", "@IndiaTV", "@TimesNow", "@DevinGibson", "@DavidRubenstein", "@ABC11WTVD", "@fox26houston", "@suthichailive", "@ustv", "@lopezobrador", "@BlackConservativePerspective", "@ytnnews24", "@AlarabyTv_News", "@kyiv_post", "@QuelindTV", "@fox5atlanta", "@mnews-tw", "@FOX32Chicago", "@TheStandardNews", "@INSIDERUSSIA", "@arte", "@tvbssisysworldnews", "@OpenmindedThinkerShow", "@KetteringFoundation", "@LetsTalkElections", "@SanaHandStitch", "@Channel3000", "@NTDBusiness", "@douglasmacgregortoday", "@bennyjohnson", "@CBSDFW", "@5news", "@FiringLine", "@Raxnews", "@RedactedNews", "@coasttvnews", "@chinaglobalsouth", "@OnePHonCignal", "@CaspianReport", "@SETBorderlessWorld", "@globalnews", "@FarronBalanced", "@indiatoday", "@SantaMonicaCloseup", "@breakingpoints", "@AmericanAlert", "@MNBWORLD", "@factsfirstph", "@OneNewsPH", "@IRANINTL", "@azizgaming35", "@restispolitics", "@AlMayadeenPrograms", "@TheDavidLinReport", "@TheWireNews", "@hysteriapodcast", "@ThaiPBS", "@TheStormMedia", "@FOX61News", "@TVBNewsHK", "@weathernorcal", "@NBC10WJAR", "@arighteousperspective", "@usefulidiots", "@CyrusJanssen", "@podsaveamerica", "@T-HouseofCGTN", "@sycagencyteam", "@legcogovhken", "@CombatVeteranReacts", "@StratNewsGlobal", "@news18India", "@TheUSNewsman", "@Fox10Phoenix", "@channel24digital", "@IndiaGlobalLeft", "@RepublicanVotersAgainstTrump", "@ktsm9news", "@DCNewsNow_", "@hotzonepodcast", "@HarrisSultanAtheist", "@applevalleynewsnow", "@wwltv", "@KING5Seattle", "@WDTNTV", "@MidwestSafety", "@afikra", "@alghadtv", "@einatwilf", "@DailyIttefaqDigital", "@ktalnews.", "@sevgininsofrasi", "@ITVNews", "@comedycellarclips", "@superkaya", "@culturefaithandpolitics", "@cbscolorado", "@ElSalvadorNoticia", "@ABC30ActionNews", "@krcrnewschannel7", "@Nexton9NEWS", "@TNN.Online", "@scrippsnews", "@sco0per", "@NewTaiwanonline", "@rfacantonese", "@TuProfeDeRI", "@ChineseFinance", "@RtvNews", "@USNewsfront", "@AtlantaNewsFirst", "@deepstateradio", "@CCTVVideoNewsAgency", "@GlobalInstituteForTomorrow", "@weloveafrica", "@CBSMiami", "@KSATnews", "@tritiyomatra", "@euronewses", "@SenatorJohnKennedy", "@CGTNEurope", "@PoliticsGirl", "@RisetoYourBestSelf", "@chinatvnews", "@VaticanNewsEN", "@NDISC", "@NarendraModi", "@DeclassifiedUK", "@4NewsNow", "@KOAMNewsNow", "@usdotgov", "@StraightArrowNews", "@AdaDeranaEnglish", "@spectrumlocalnews", "@fox5dc", "@adam.taggart", "@greaterchinalive", "@oneindia", "@Taskandpurpose", "@ProgressivePoliticsNetwork", "@JA21official", "@ChannelsTelevision", "@witnessdocumentaries", "@stateofapod", "@wenzhaoofficial", "@nbcsandiego", "@Global_Vision", "@Mr.F", "@Okayrick", "@SpeakerJohnson", "@resonanceinfo", "@CCTV", "@nitinternational", "@jerusalempressclub", "@cts3scompany", "@morningstar", "@CanalCatorcemx", "@vtv24", "@KernowDamo", "@jtbc_news", "@ThePrintIndia", "@EkattorTelevision", "@allisrael", "@TheAfricaNewsNetwork", "@TheProfGShow", "@24%D0%9A%D0%B0%D0%BD%D0%B0%D0%BB", "@MiguelRuizCalvo", "@InsiderNews", "@WeAreIowa", "@GregTeachesEnglish", "@mizzimanewsTV", "@SLICE_Experts", "@StateBoyzzz", "@NYTPodcasts", "@KendelReacts", "@AsharqNews", "@kitv", "@GoldmanSachs", "@7NewsDC", "@TheThinkingMuslim", "@TheRosenbergReport", "@%E8%A7%80%E9%BB%9E", "@TLDRnews", "@azfamily", "@ravishkumar.official", "@%E8%B1%90%E5%AF%8C", "@PNNPTS", "@CallMeBackPodcast", "@UsPresstime", "@News4JAX", "@marines", "@Denver7", "@cnnee", "@Timothykellersermonsus", "@ecowasparliament7252", "@HC.TAIWANPLUS", "@kcrg", "@BBCHindi", "@ATNBanglanews", "@Epiphany520", "@BanglaVisionNEWS", "@WSJopinion", "@LeDessousdesCartesARTE", "@NTDAPTV", "@LeejaMiller", "@Around-News", "@sinyornews", "@timesnownavbharat", "@DailyWirePlus", "@miscronicas_", "@abc3340", "@MediaEducationFoundation", "@TTV_NEWS", "@NBCChicago", "@JiangFengTimes", "@CCTVCH", "@SekretariatPresiden", "@Whntnews19huntsville", "@CtsTw", "@Longtunman", "@JackCocchiarellaShow", "@StephenGardner1", "@ThomasSowellTV", "@TheStandardWealth", "@washingtonexaminer", "@DiplomatischeAkademieWien", "@newsxlive", "@almayadeenenglish", "@ATNNewsLive", "@52NewsClub", "@TVOAX", "@reinventmoney", "@SinEmbargoAlAire", "@THECHANAKYADIALOGUESENGLISH", "@LFRFAMILY", "@KSNTNews27", "@TomBilyeu", "@ResoluteSquare", "@justinpodur", "@suchomimus9921", "@6NewsAU", "@courageousMedia", "@TimesNowWorld", "@superfm985program", "@MuslimNetworkTV", "@YishaiFleisherTV", "@Daily_US_Reporter", "@jovempannews", "@RadioTelevisionSuisse", "@LAOCTAVA", "@CenterforChinaandGlobalization", "@ThePalestinePod", "@DissidentDialogues", "@Chinanewsandinsights", "@GuoVision-TV", "@dugunfotoTR", "@voicebanglatv", "@unian", "@todayth", "@clearvaluetax9382", "@sbsnews8", "@PalmBeachPost", "@dbcnewstv", "@tvbsmoney", "@yahootw", "@WZDXNewsFOX54", "@TheEconomicTimes", "@KATUNews", "@uncutafricalive", "@Radio-Svoboda", "@globalnewspodcast2113", "@NTDtonight", "@FoundationforMiddleEastPeace", "@USNewsVault", "@NCUSCR", "@blastinfo", "@tribunnews", "@ebcCTime", "@artetvdocumentales", "@NEWS9LIVE", "@pryamiy", "@%E4%B8%AD%E5%A4%A9%E8%B2%A1%E7%B6%93%E9%A0%BB%E9%81%93CtiFinance", "@lawfaremedia", "@vandehomnay", "@MaasrangaNewsbd", "@9NewsAUS", "c/LezzetY%C3%B6resi", "@dimitrilascaris3051", "@kelolandnews", "@SPEAKS_TV", "@TVBSNEWS02", "@DDnews", "@NBC10Boston", "@ketchupcraft1", "@USATonight", "@CodeBlueCam", "@whatadaypodcast", "@MESGlobal", "@SilkWayQazaqstan", "@UNITED24media", "@AmericanTimes_News", "@aseananalytics", "@setn", "@BDViews", "@ThePressDemocrat", "@TheChinaShow", "@TheJuliaLaRocheShow", "@KOLKATATV", "@AlArabiyaEnglish", "@Bloomberg_Live", "@Quillette", "@Deshtvnews", "@SansadTV", "@Rappler", "@ChineseArmy", "@CurrentTimeTV", "@julioastillero", "@BaronGlobal", "@IISSorg", "@lanacion", "@MBCNEWS11", "@nbcwashington", "@NMFNews", "@Politicon", "@27newsfirst", "@PacificReport", "@KhitThitMedia", "@SIEPRatStanford", "@cnnchile", "@weukrainetv", "@beltavideo", "@Geopolitics_Insider", "@pesblackgaming4733", "@elpuntoblancoyoutube", "@capitolreport", "@RompevientoTV", "@tvotoday", "@zillur_rahman", "@onecountry9918", "@AlexMercouris", "@Barta24", "@VOAKorea", "@3mitinews", "@rfaburmese", "@newwavenewstv", "@CCBPeace", "@BeritaRTMBES", "@inewsplus", "@PiersMorganUncensored", "@kitco", "@TheRussianDude", "@johnnyharris", "@forces_news", "@TV9Bharatvarsh", "@EverydayPundit", "@ReedTimmerWx", "@EuroResilience", "@alanjones", "@WiYard", "@CBS42", "@bbcnewsarabic", "@FactsMatterRoman", "@NYCNews.", "@KantipurTVHD", "@tvbnewsofficial", "@tvtokyobiz", "@News18Bangla", "@ANNnewsCH", "@TheDemocraticNewscaster", "@Mr.F2", "@RealVisionFinance", "@almayadeennews", "@mbcradio_sisa", "c/Croch%C3%AACirlei", "@jesusescobartovar3837", "@NewsNationTV", "@NationalHasbara", "@thehughhewittshow", "@EconomyAndGeopolitics", "@irrawaddynews1993", "@IndependentUSA", "@militarysummary", "@U.S.NewsToday", "@AZPBSNow", "@newzroomafrika5914", "@Criti_Quest", "@HoltHanley", "UCKp3EIUXRm_kgeVpT0HAsog", "UCGdHm-zA3GgU9BAZfPD0L0g", "@DWKhaledMuhiuddinJanteChay", "@atnnewsltd", "@tribunvideo", "@MinisterioR.C.Sproul", "@VoicesThroughHistory", "@ForbesBreakingNewsLive", "@TheJewishChronicle", "@fox40", "@indianexpress", "@NationalGovernorsAssociation", "@KSBYTV", "@Ntvbdnews", "@BestCongress", "@Insider", "@Freedom520buy", "@theplebreporter", "@rtvenoticias", "@electronsinc", "@FRANCE24", "@AnkaNewsOfficial", "@NavalNews", "@fox5sd", "@Mahmood_OD", "@5channel", "@presidentialclimatecommiss407", "@SOH_TV", "@TheRajdharma", "@OversightDems", "@novynyua", "@cbsphilly", "@MEXICOINFORMA", "@CFTKTVNWBC", "@DVBTVnews", "@DBLive", "@danwoottonoutspoken", "@pmosingapore", "@SenChuckGrassley", "@bbcnewschinese", "@USNewsTonight.", "@seychas", "@newslaundry", "@DeptofDefense", "@WOAIVideo", "@DDIndia", "@CronicasdeUcrania", "@aajtak", "@KETV", "@57ETFN", "@OPB", "@ZaxidNetTV", "@Tbn24usa", "@NewsChannelNebraska", "@TV-od5nb", "@TheDispatchPods", "@LACityview35", "@arkansaspoliceactivity", "@nataliebrunell", "@ruedopolitico", "@CBSAustin", "@RuthlessPodcast", "@FirstCoastNews", "@TheCoalitionRadioNetwork", "@WxChasing", "@HOYTVHK", "@Changetvpress", "@PoloPugaMx", "@RoanaSalles", "@%E6%95%B8%E5%AD%97%E5%8F%B0%E7%81%A3", "@sxh", "@LoneRanger777", "@wealth1974", "@PTVWorldOfficial", "@truedailynews", "@tbnewswatch", "@ITNArchive", "@democraticTaiwanChannel", "@AustralianBankingAssociation", "@NewStatesman", "@yonhapnewstv23", "@onpayments", "@RepublicWorld", "@Mathsuppro", "@noticias", "@republicbangla", "@mediamagikgroup", "@mbn", "@94politics", "@NewsCentralAfrica", "@TintucthoisuVietnam", "@Newspaper1y", "@ElPeriodistaCamorrista", "@DanielleDiMartinoBoothQI", "@GlennGreenwald", "@MarkRamos", "@deepdivewithshawncfettig7708", "@TianLiangTimes", "@khodorkovskylive", "@UKRAINETODAY24", "@ictv", "@gongzishen", "@war_my", "@Fox29Philly", "@rafalhm", "@RFACHINESE", "@FISMTV", "@politiscapetv", "@%E5%B9%B4%E4%BB%A3%E6%96%B0%E8%81%9ECH50", "@professornez", "@DnielleCabrera", "@FTV_Forum", "@bangkaposofficial", "@indianews", "@ChinaInsiderWithDavidZhang", "@AlertaMexicoOficial", "@AEKMediadaily", "@OpentoDebate", "@THEBVNEWS24", "@NewsWatch12", "@mariafarias-confeitariaartesan", "@KBS_1Radio", "@wgtvhk", "@voaindonesia", "@QNSVoice", "@tvchosunnews", "@yoonique2929", "@PhilosProject", "@marclamonthillofficial", "@IWMVienna", "@douginexile", "@CRITICADURAMX", "@nightmareboyzz", "@stevenvanmetre5087", "@voxifa", "@weathermanplus", "@WTOL11", "@alexisburelo", "@newstapa", "@JoseLapiz", "@todayamericanews", "@ACurrentAffair9", "@fox43", "@WIFRTV", "@MuYangShow", "@DDNEWSJAMMU", "@OmTVUA", "@ChinaDeepDive-qg5nl", "@SenatorDurbin", "@accuweather", "@matichontv", "@NEWS24TV", "@ankaisraelnews", "@SimonWDC", "@vlogcasterarmanddean8744", "@DaveTheLawyer", "@masterinsightmedia", "@UKImmigrations", "@NachoRgzC", "@bigarena520", "@kalbelanews24", "@selwyn1882", "@AlexandreGarciaOficial", "@vailsymposium8150", "@CarnegieEndowment", "@newsebc", "@TheDailyStarNews", "@TribunJatengOfficial", "@GUNaSHOW", "@ScrollIn", "@official.omarquinonez", "@GriptMedia", "@StepNewsAgency", "@newskbs", "@9MCOT", "@reefrebels", "@cahdecora", "@SCOOTERCASTER", "@wehotv", "@news5cleveland");

        SingleBrowseClient client = new SingleBrowseClient(confs.getFirst()) {
            @Override
            public Point getClickLocation() {
                return null;
            }
            @Override
            public void run() {
                int count = 0;
                for (String channel : channels) {
                    try {
                        browserPanel.browser.navigation().loadUrlAndWait("https://www.youtube.com/" + channel + "/videos",
                                Duration.ofSeconds(30));
                        Thread.sleep(10000);
                        Document doc = browserPanel.browser.mainFrame().flatMap(Frame::document).orElse(null);
                        if (doc == null) {
                            System.err.println(channel);
                            continue;
                        }
                        String name = "";
                        String desc = "";
                        List<String> titles = new ArrayList<>();
                        // #page-header h1[aria-label] span
                        // #page-header yt-description-preview-view-model truncated-text-content > span.yt-core-attributed-string
                        // #contents #details a#video-title-link
                        Optional<Element> nameEle = doc.findElementByCssSelector("#page-header h1[aria-label] span");
                        if (nameEle.isPresent()) {
                            name = nameEle.get().innerText().trim();
                        }
                        Optional<Element> descEle = doc.findElementByCssSelector("#page-header yt-description-preview-view-model truncated-text-content > span.yt-core-attributed-string");
                        if (descEle.isPresent()) {
                            desc = descEle.get().innerText().trim();
                        }
                        List<Element> videos = doc.findElementsByCssSelector("#contents #details a#video-title-link");
                        for (Element video : videos) {
                            titles.add(video.innerText().trim());
                        }
                        //
                        Map<String, Object> result = new HashMap<>();
                        result.put("channel", channel);
                        result.put("name", name);
                        result.put("description", desc);
                        result.put("titles", titles);
                        FileTool.appendFile(Collections.singletonList(JSON.toJSONString(result)), "./channel-info.txt");
                        System.out.println(++count + " / " + channels.size());
                    } catch (Exception e) {
                        System.err.println(channel);
                    }

                }
            }
        };
        new Thread(client).start();
    }

    public static void main(String[] args) throws Exception {
        toPrompts();
    }
}

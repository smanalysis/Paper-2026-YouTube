package top.socialbot.tools;

import org.jsoup.Connection;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.net.InetSocketAddress;
import java.net.Proxy;

public class JsoupHttpTool {
    private static final Logger logger = LoggerFactory.getLogger("JsoupHttpTool");

    public static Proxy buildProxy(String addr, int port) {
        if (addr != null && !addr.isEmpty() && port > 0) {
            return new Proxy(Proxy.Type.HTTP, new InetSocketAddress(addr, port));
        } else {
            return Proxy.NO_PROXY;
        }
    }

    public static String getText(String url, Proxy proxy) {
        try {
            return Jsoup.connect(url).proxy(proxy).execute().body();
        } catch (Exception e) {
            return "";
        }
    }

    public static Document getHTML(String url, Proxy proxy) {
        try {
            return Jsoup.connect(url).proxy(proxy).get();
        } catch (Exception e) {
            return null;
        }
    }

    public static String postText(String url, String body, Proxy proxy) {
        try {
            // Send POST request
            Connection.Response response = Jsoup.connect(url)
                    .proxy(proxy)
                    .method(Connection.Method.POST)  // Specify POST method
                    .header("Content-Type", "text/plain") // Set Content-Type header
                    .requestBody(body)  // Add raw string as request body
                    .execute(); // Execute the request
            return response.body();
        } catch (Exception e) {
            logger.warn(SystemTool.getStackTrace(e));
            return "";
        }
    }
}

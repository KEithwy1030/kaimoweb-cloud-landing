/**
 * 凯默工作室 - 支付后端 (Cloudflare Worker)
 * 负责人：处理虎皮椒支付的发起与回调验证
 */

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // 允许跨域
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    // 路由：发起支付
    if (url.pathname === "/pay" && request.method === "POST") {
      try {
        const body = await request.json();
        const { planId, amount } = body;

        // --- 配置区 (审核通过后填入) ---
        const config = {
          appid: "YOUR_APP_ID", // 填入虎皮椒 AppID
          secret: "YOUR_APP_SECRET", // 填入虎皮椒 AppSecret
          api_url: "https://api.xunhupay.com/payment/do.html",
          notify_url: "https://kaimoweb-pay-api.keith-wyong.workers.dev/callback", // 填入你的 Worker 访问地址
          return_url: "https://kaimoweb.cloud",
        };

        const trade_order_id = `ORDER_${Date.now()}`;
        const params = {
          appid: config.appid,
          title: `KaiMo Studio - ${planId}`,
          trade_order_id: trade_order_id,
          total_fee: amount, // 单位：元
          time: Math.floor(Date.now() / 1000).toString(),
          notify_url: config.notify_url,
          return_url: config.return_url,
          nonce_str: Math.random().toString(36).substring(2),
        };

        // 计算签名 (MD5)
        const hash = await generateSign(params, config.secret);
        params.hash = hash;

        // 向虎皮椒发起请求
        const response = await fetch(config.api_url, {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: new URLSearchParams(params).toString(),
        });

        const result = await response.json();
        return new Response(JSON.stringify(result), {
          headers: { ...corsHeaders, "Content-Type": "application/json" },
        });
      } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), {
          status: 500,
          headers: corsHeaders,
        });
      }
    }

    // 路由：支付回调 (虎皮椒服务器通知我们的接口)
    if (url.pathname === "/callback" && request.method === "POST") {
      const data = await request.formData();
      const params = Object.fromEntries(data.entries());

      // 注意：这里需要验证签名防止伪造
      // 如果验证通过，这里可以处理业务逻辑，比如记录订单状态等
      console.log("收到支付回调:", params);

      return new Response("success"); // 必须返回 success
    }

    return new Response("KaiMo API Server is Running", { status: 200 });
  },
};

/**
 * 虎皮椒签名生成算法
 */
async function generateSign(params, secret) {
  const keys = Object.keys(params).sort();
  const sortedStr = keys.map(k => `${k}=${params[k]}`).join("&") + secret;

  const msgUint8 = new TextEncoder().encode(sortedStr);
  const hashBuffer = await crypto.subtle.digest("MD5", msgUint8);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
}

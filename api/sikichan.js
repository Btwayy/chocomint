export default function handler(req, res) {
  const targetTime = new Date("2026-03-14T07:35:00+09:00");
  const now = new Date();

  res.setHeader('Content-Type', 'text/html; charset=utf-8');

  if (now < targetTime) {
    return res.status(200).send(`
      <body style="display:flex;align-items:center;justify-content:center;height:100vh;margin:0;background:#fffafb;color:#cc99a2;font-family:sans-serif;">
        <p>能从源码里找到这里，不愧是你！でもまだ秘密だよ～ ʕ •ᴥ•ʔ 🌸</p>
      </body>
    `);
  }

  res.status(200).send(`
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>White Day Letter🤍</title>
        <style>
            :root { --accent: #ff8fa3; --text: #4a4a4a; }
            body { margin: 0; min-height: 100vh; font-family: sans-serif; display: flex; align-items: center; justify-content: center; overflow-x: hidden; }
            .bg {
                position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background-image: url('/bg.jpg'); background-size: cover;
                background-position: center; z-index: -2;
            }
            .overlay {
                position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                background: linear-gradient(to bottom, rgba(255, 250, 251, 0.85), rgba(255, 255, 255, 0.65));
                backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); z-index: -1;
            }
            .sakura {
                position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
                pointer-events: none; z-index: 99; overflow: hidden;
            }
            .petal {
                position: absolute; width: 15px; height: 15px;
                background: #ffb7c5; border-radius: 150% 0 150% 150%;
                opacity: 0.7; animation: vfall linear infinite;
            }
            @keyframes vfall { 0% { top: -10%; transform: translateX(0) rotate(0); } 100% { top: 110%; transform: translateX(100px) rotate(360deg); } }
            .card {
                position: relative; z-index: 1;
                background: rgba(255, 255, 255, 0.85);
                padding: 40px; border-radius: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.05);
                max-width: 500px; width: 85%;
                line-height: 2; color: var(--text);
                animation: vfadeIn 1.2s ease-out;
            }
            h1 { color: var(--accent); font-size: 1.4rem; margin-bottom: 25px; border-bottom: 1px solid #ffe4e8; padding-bottom: 10px; }
            p { margin-bottom: 20px; white-space: pre-wrap; font-size: 1rem; }
            .footer { margin-top: 40px; text-align: right; color: #cc99a2; font-size: 0.9rem; }
            @keyframes vfadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        </style>
    </head>
    <body>
        <div class="bg"></div>
        <div class="overlay"></div>
        <div class="sakura" id="canvas"></div>
        <div class="card">
          <h1>To: 光漪</h1>
          <p>能在源码里找到这里，不愧是你！这封信是特别留给你的...</p>
          <p>怎么样我的这个小惊喜^ ^ 不知道你会不会喜欢，但是我还是很自满的嘿嘿。</p>
          <p>有没有拆开礼物呢？原谅我任性的买了这些，希望是你觉得可以用的上的东西。</p>
          <p>那个小包包是我们一起去神保町看跑鞋的那天我给你看的，你说很可爱い～所以我就买啦，和我的背包是揃い款！也许可以爬山的时候把四季ちゃん放在里面，或者跑步的时候挂在胳膊上放手机也很方便！</p>
          <p>至于耳机，是你之前告诉我, 你现在的耳机是拿的别人的,然后一直用到现在了。 不知道你说这些话的时候心情是如何的，但是我会猜测你是需要一个自己的耳机的～ 而且我也很想当你带上耳机学习的时候，会想到这是家辉さん送的，就会稍微多些やる気！就像我一直陪在身边一样^ ^</p>
          <p>我就不在这里写太多啦，相信你还有其他要看的东西是吧嘿嘿！</p>
          <p>白色情人节快乐啦！谢谢你的ガトーショコラ！所以我也想送你一些惊喜！</p>
          <p>真的很喜欢你🌿，希望可以很快见面啦～</p>
          <p>これからも一緒にいられたら嬉しい</p>
            <div class="footer">
                2026.03.14<br>
                家辉🦙
            </div>
        </div>
        <script>
            function start() {
                const c = document.getElementById('canvas');
                for (let i = 0; i < 30; i++) {
                    const p = document.createElement('div');
                    p.className = 'petal';
                    p.style.left = Math.random() * 100 + '%';
                    p.style.top = Math.random() * -20 + '%';
                    p.style.animationDuration = Math.random() * 5 + 5 + 's';
                    p.style.animationDelay = Math.random() * 5 + 's';
                    c.appendChild(p);
                }
            }
            start();
        </script>
    </body>
    </html>
  `);
}
export default function handler(req, res) {
  // 设置为 2026年3月14日 07:30 (JST)
  const targetTime = new Date("2026-03-14T07:30:00+09:00").getTime();
  const now = Date.now();

  if (now >= targetTime) {
    res.status(200).json({
      active: true,
      payload_url: "/kuma.mp4",
      header_text: "ハッピーホワイトデー！",
      meta_desc: "ハッピーホワイトデー！<br><br>実はね、くまちゃんから「こなみちゃんにメッセージがある」って言われたから、私が代わりに動画にしておいたよ。<br><br>くまちゃんからのヒントを頼りに出発してみてね！",
      ui_config: {
      t: "video",
      s: "source",
      m: "video/mp4"
      }
    });
  } else {
    res.status(200).json({
      active: false,
      timestamp_diff: targetTime - now
    });
  }
}


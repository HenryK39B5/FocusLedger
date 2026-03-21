function short(value: string, head = 6, tail = 4) {
  if (value.length <= head + tail + 3) {
    return value;
  }
  return `${value.slice(0, head)}...${value.slice(-tail)}`;
}

function getParam(url: string, key: string) {
  try {
    const parsed = new URL(url);
    return parsed.searchParams.get(key) ?? "";
  } catch {
    return "";
  }
}

export function summarizeWechatSourceIdentifier(identifier: string) {
  const biz = getParam(identifier, "__biz");
  const action = getParam(identifier, "action");
  if (identifier.includes("profile_ext")) {
    const actionLabel = action === "report" ? "report token" : action === "urlcheck" ? "urlcheck" : "profile_ext";
    return biz ? `${actionLabel} · biz ${short(biz)}` : actionLabel;
  }
  if (identifier.includes("mp.weixin.qq.com/s")) {
    return biz ? `article link · biz ${short(biz)}` : "article link";
  }
  if (identifier.includes("action=home")) {
    return biz ? `home link · biz ${short(biz)}` : "home link";
  }
  return "wechat source";
}

export function isDeleteableWechatSource(identifier: string) {
  return identifier.includes("mp.weixin.qq.com");
}

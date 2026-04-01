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

export function summarizeWechatCredentialLink(rawLink?: string | null) {
  if (!rawLink) {
    return "尚未绑定来源凭据";
  }
  const biz = getParam(rawLink, "__biz");
  const action = getParam(rawLink, "action");
  if (rawLink.includes("profile_ext")) {
    const actionLabel =
      action === "report" ? "report 凭据" : action === "urlcheck" ? "urlcheck 凭据" : "profile_ext 凭据";
    return biz ? `${actionLabel} / biz ${short(biz)}` : actionLabel;
  }
  return "公众号凭据";
}

export function summarizeWechatHomeLink(homeLink?: string | null, biz?: string | null) {
  if (homeLink?.includes("action=home")) {
    const homeBiz = getParam(homeLink, "__biz") || biz || "";
    return homeBiz ? `主页链接 / biz ${short(homeBiz)}` : "主页链接";
  }
  if (biz) {
    return `biz ${short(biz)}`;
  }
  return "公众号来源";
}

export function credentialStatusLabel(status: string) {
  switch (status) {
    case "valid":
      return "可用";
    case "refresh_required":
      return "需刷新凭据";
    case "invalid":
      return "凭据无效";
    default:
      return "待验证";
  }
}

export function formatDateTimeShanghai(value?: string | null) {
  if (!value) {
    return "--";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value.replace("T", " ").slice(0, 19);
  }
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(parsed);
}

"use client";

import Link from "next/link";
import { ClipboardCopy, Plus } from "lucide-react";
import { useState } from "react";
import { useMutations } from "@/lib/queries";
import type { WechatHomeLinkResolveResult } from "@/lib/types";
import { ActionButton, Input, Label, PageFrame, SectionTitle, Textarea } from "@/components/ui";

function normalizeGroupPath(path?: string | null) {
  if (!path) {
    return "";
  }
  return path
    .split(/[\\/]+/)
    .map((part) => part.trim())
    .filter(Boolean)
    .join("/");
}

function parseTags(value: string) {
  return value
    .split(/[,\n，]/)
    .map((tag) => tag.trim())
    .filter(Boolean)
    .filter((tag, index, list) => list.indexOf(tag) === index);
}

export default function AddSourcePage() {
  const mutations = useMutations();

  const [articleUrl, setArticleUrl] = useState("");
  const [resolveResult, setResolveResult] = useState<WechatHomeLinkResolveResult | null>(null);
  const [resolveMessage, setResolveMessage] = useState("");
  const [resolveLoading, setResolveLoading] = useState(false);

  const [sourceName, setSourceName] = useState("");
  const [sourceBiz, setSourceBiz] = useState("");
  const [publicHomeLink, setPublicHomeLink] = useState("");
  const [credentialLink, setCredentialLink] = useState("");
  const [sourceGroup, setSourceGroup] = useState("");
  const [sourceTags, setSourceTags] = useState("");
  const [sourceDescription, setSourceDescription] = useState("");
  const [formMessage, setFormMessage] = useState("");

  async function handleResolveHome() {
    const value = articleUrl.trim();
    if (!value) {
      setResolveMessage("请先输入一篇公众号文章链接。");
      return;
    }

    setResolveLoading(true);
    setResolveMessage("");
    try {
      const result = await mutations.resolveWechatHome.mutateAsync(value);
      setResolveResult(result);
      setResolveMessage(result.message ?? "公众号主页链接解析完成。");
      if (result.source_name) {
        setSourceName((current) => current || result.source_name || "");
      }
      if (result.biz) {
        setSourceBiz(result.biz);
      }
      if (result.public_home_link) {
        setPublicHomeLink(result.public_home_link);
      }
    } catch (error) {
      setResolveResult(null);
      setResolveMessage(error instanceof Error ? error.message : "公众号主页链接解析失败。");
    } finally {
      setResolveLoading(false);
    }
  }

  async function handleCreateSource() {
    setFormMessage("");

    if (!sourceName.trim() || !sourceBiz.trim() || !credentialLink.trim()) {
      setFormMessage("请填写来源名称、公众号 biz 和来源凭据链接。");
      return;
    }

    if (!credentialLink.includes("profile_ext")) {
      setFormMessage("这里需要粘贴完整的 profile_ext 链接。");
      return;
    }

    try {
      await mutations.createSource.mutateAsync({
        name: sourceName.trim(),
        source_type: "wechat_public_account",
        biz: sourceBiz.trim(),
        public_home_link: publicHomeLink.trim() || null,
        credential_link: credentialLink.trim(),
        source_group: normalizeGroupPath(sourceGroup) || null,
        tags: parseTags(sourceTags),
        description: sourceDescription.trim() || null,
      });
      setFormMessage("来源已创建。现在可以去“文章获取”页面执行同步。");
      setCredentialLink("");
    } catch (error) {
      setFormMessage(error instanceof Error ? error.message : "创建来源失败。");
    }
  }

  async function handleCopy(text?: string | null) {
    if (!text) {
      return;
    }
    await navigator.clipboard.writeText(text);
    setResolveMessage("已复制到剪贴板。");
  }

  return (
    <PageFrame
      title="添加公众号来源"
      subtitle="先从任意一篇真实公众号文章解析公众号身份，再绑定一条有效的 profile_ext 凭据，完成来源创建。"
      actions={
        <>
          <Link href="/sources">
            <ActionButton variant="ghost">返回来源管理</ActionButton>
          </Link>
          <Link href="/collect">
            <ActionButton variant="ghost">前往文章获取</ActionButton>
          </Link>
        </>
      }
    >
      <div className="grid gap-6 xl:grid-cols-[1.02fr_0.98fr]">
        <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
          <SectionTitle
            title="第一步：解析公众号身份"
            subtitle="输入任意一篇真实公众号文章链接，提取公众号 biz 和主页链接。"
          />
          <div className="space-y-4">
            <div>
              <Label>文章链接</Label>
              <Input
                value={articleUrl}
                onChange={(event) => setArticleUrl(event.target.value)}
                placeholder="https://mp.weixin.qq.com/s/..."
              />
            </div>
            <div className="flex flex-wrap gap-3">
              <ActionButton variant="solid" onClick={handleResolveHome} disabled={resolveLoading}>
                <ClipboardCopy size={14} className="mr-2" />
                {resolveLoading ? "解析中..." : "解析主页链接"}
              </ActionButton>
              <ActionButton
                variant="ghost"
                onClick={() => handleCopy(resolveResult?.public_home_link)}
                disabled={!resolveResult?.public_home_link}
              >
                <ClipboardCopy size={14} className="mr-2" />
                复制主页链接
              </ActionButton>
            </div>
            {resolveMessage ? (
              <p className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-white/70">
                {resolveMessage}
              </p>
            ) : null}
            {resolveResult ? (
              <div className="rounded-[24px] border border-white/10 bg-black/20 p-4">
                <div className="grid gap-3 text-sm text-white/70">
                  <div>
                    <p className="text-white/50">公众号名称</p>
                    <p className="mt-1 text-white">{resolveResult.source_name || "未识别"}</p>
                  </div>
                  <div>
                    <p className="text-white/50">公众号 biz</p>
                    <p className="mt-1 break-all text-white">{resolveResult.biz || "未提取到"}</p>
                  </div>
                  <div>
                    <p className="text-white/50">主页链接</p>
                    <p className="mt-1 break-all text-white">{resolveResult.public_home_link || "未提取到"}</p>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </section>

        <section className="rounded-[28px] border border-white/10 bg-white/5 p-5">
          <SectionTitle
            title="第二步：创建来源"
            subtitle="把一条有效的 profile_ext 凭据绑定到这个公众号来源中。"
          />
          <div className="space-y-4">
            <div>
              <Label>来源名称</Label>
              <Input value={sourceName} onChange={(event) => setSourceName(event.target.value)} placeholder="例如：三联生活周刊" />
            </div>
            <div>
              <Label>公众号 biz</Label>
              <Input value={sourceBiz} onChange={(event) => setSourceBiz(event.target.value)} placeholder="例如：MzA4MjQxNjQzMA==" />
            </div>
            <div>
              <Label>主页链接</Label>
              <Input
                value={publicHomeLink}
                onChange={(event) => setPublicHomeLink(event.target.value)}
                placeholder="https://mp.weixin.qq.com/mp/profile_ext?action=home&__biz=..."
              />
            </div>
            <div>
              <Label>来源凭据链接</Label>
              <Textarea
                value={credentialLink}
                onChange={(event) => setCredentialLink(event.target.value)}
                placeholder="https://mp.weixin.qq.com/mp/profile_ext?action=report&..."
              />
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <Label>分组路径</Label>
                <Input value={sourceGroup} onChange={(event) => setSourceGroup(event.target.value)} placeholder="例如：投研/宏观" />
              </div>
              <div>
                <Label>标签</Label>
                <Input value={sourceTags} onChange={(event) => setSourceTags(event.target.value)} placeholder="例如：宏观, 深度, 财经" />
              </div>
            </div>
            <div>
              <Label>备注</Label>
              <Textarea
                value={sourceDescription}
                onChange={(event) => setSourceDescription(event.target.value)}
                placeholder="记录这个来源的定位、关注理由或观察重点。"
              />
            </div>
            <ActionButton variant="solid" onClick={handleCreateSource} disabled={mutations.createSource.isPending}>
              <Plus size={14} className="mr-2" />
              创建来源
            </ActionButton>
            {formMessage ? <p className="text-sm text-white/70">{formMessage}</p> : null}
          </div>
        </section>
      </div>
    </PageFrame>
  );
}

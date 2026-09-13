import { QuartzTransformerPlugin } from "../types"
import { visit } from "unist-util-visit"
import type { Root, Element } from "hast"
import type { VFile } from "vfile"

export const VideoExtractor: QuartzTransformerPlugin = () => {
  return {
    name: "VideoExtractor",
    markdownPlugins() {
      return [
        () => (tree, file) => {
          const content = String(file.value || "")
          const fm = (file.data.frontmatter as Record<string, any>) ?? {}
          file.data.frontmatter = fm

          const isExplicitPortfolio = fm.portfolio === true || fm.portfolio === "true"
          const isExplicitNonPortfolio = fm.portfolio === false || fm.portfolio === "false"

          const tags = Array.isArray(fm.tags) ? fm.tags : []
          const hasPortfolioTag = tags.some(
            (t: any) =>
              typeof t === "string" &&
              (t.toLowerCase() === "portfolio" || t === "作品集"),
          )

          const isPortfolio =
            !isExplicitNonPortfolio && (isExplicitPortfolio || hasPortfolioTag)

          if (isPortfolio) {
            fm.portfolio = true
            file.data.portfolio = true
          }

          // 1. Dynamic Title Extraction (if frontmatter title is missing or default stem)
          if (!fm.title || fm.title === file.stem || fm.title === "Untitled" || fm.title === "index") {
            const h1Match = content.match(/^#\s+(.+)$/m)
            if (h1Match) {
              const cleanTitle = h1Match[1].trim()
              fm.title = cleanTitle
              file.data.title = cleanTitle
            } else if (file.data.slug && file.data.slug.endsWith("/index")) {
              const dirName = file.data.slug.split("/")[0]
              const folderTitles: Record<string, string> = {
                Art: "审美积累",
                MathAndPhysics: "基础知识积累",
                Portfolio: "个人开发工具",
                "Tech-Notes": "技术笔记",
              }
              const folderTitle = folderTitles[dirName] || dirName
              fm.title = folderTitle
              file.data.title = folderTitle
            }
          }

          // 2. Dynamic Description Extraction (if frontmatter description is missing)
          if (!fm.description) {
            const bodyOnly = content
              .replace(/^---[\s\S]*?---\r?\n?/, "")
              .replace(/<div class="glass-video-card"[\s\S]*?<\/div>/gi, "")
              .replace(/<video[\s\S]*?<\/video>/gi, "")
              .replace(/\$\$[\s\S]*?\$\$/g, "")
              .replace(/<[^>]+>/g, "")
            const lines = bodyOnly.split("\n")
            for (const rawLine of lines) {
              const line = rawLine.trim()
              if (
                !line ||
                line.startsWith("#") ||
                line.startsWith("---") ||
                line.startsWith("```") ||
                line.startsWith("!") ||
                line.startsWith(">") ||
                line.startsWith("|") ||
                line.startsWith("$$") ||
                line.startsWith("$") ||
                line.startsWith("<!--")
              ) {
                continue
              }
              // Clean list bullets and inline markdown formatting
              const cleanedText = line
                .replace(/^[-*+]\s+/, "")
                .replace(/\[\[[^\]|]+\|?([^\]]*)\]\]/g, "$1")
                .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
                .replace(/[*_`~]/g, "")
                .trim()

              if (cleanedText.length > 10) {
                const desc = cleanedText.length > 160 ? cleanedText.slice(0, 157) + "..." : cleanedText
                fm.description = desc
                file.data.description = desc
                break
              }
            }
          }

          // 3. Video Extraction:
          // Check frontmatter first (portfolio_video or video)
          let videoUrl = fm.portfolio_video || fm.video

          // If not specified, scan markdown body for <video ... data-src="..."> or src="..."
          if (!videoUrl) {
            const dataSrcMatch = content.match(/<video[^>]+data-src=["']([^"']+)["']/i)
            if (dataSrcMatch) {
              videoUrl = dataSrcMatch[1]
            } else {
              const srcMatch = content.match(/<video[^>]+src=["']([^"']+)["']/i)
              if (srcMatch) {
                videoUrl = srcMatch[1]
              } else {
                const sourceMatch = content.match(/<source[^>]+src=["']([^"']+)["']/i)
                if (sourceMatch) {
                  videoUrl = sourceMatch[1]
                } else {
                  // Direct .mp4/.webm link in content
                  const directMatch = content.match(
                    /https?:\/\/[^\s"'<>]+\.(?:mp4|webm|mov)(?:\?[^\s"'<>]*)?/i,
                  )
                  if (directMatch) {
                    videoUrl = directMatch[0]
                  }
                }
              }
            }
          }

          if (videoUrl) {
            fm.video = videoUrl
            file.data.video = videoUrl
          }

          // 4. Cover Mode & Explicit Cover Extraction
          const rawCover = String(
            fm.portfolio_cover ?? fm.cover ?? fm.cover_mode ?? "",
          ).trim()
          const lowerCover = rawCover.toLowerCase()

          let explicitMode: "frame" | "image" | undefined
          let explicitCoverUrl: string | undefined

          if (["frame", "video", "第一帧", "first_frame", "video_frame"].includes(lowerCover)) {
            explicitMode = "frame"
          } else if (["image", "img", "图片", "第一张图片", "first_image"].includes(lowerCover)) {
            explicitMode = "image"
          } else if (
            rawCover &&
            (rawCover.startsWith("http://") ||
              rawCover.startsWith("https://") ||
              rawCover.startsWith("./") ||
              rawCover.startsWith("/") ||
              rawCover.includes("."))
          ) {
            explicitMode = "image"
            explicitCoverUrl = rawCover
          }

          ;(file.data as any).explicitCoverMode = explicitMode
          ;(file.data as any).explicitCoverUrl = explicitCoverUrl
        },
      ]
    },
    htmlPlugins() {
      return [
        () => (tree: Root, file: VFile) => {
          const fm = (file.data.frontmatter as Record<string, any>) ?? {}
          if (!fm.portfolio) return

          // Search HAST tree for the first <img>
          let firstHtmlImg: string | undefined
          visit(tree, "element", (node: Element) => {
            if (
              !firstHtmlImg &&
              node.tagName === "img" &&
              node.properties &&
              typeof node.properties.src === "string"
            ) {
              firstHtmlImg = node.properties.src
            }
          })

          let resolvedImage = (file.data as any).explicitCoverUrl

          if (!resolvedImage && firstHtmlImg) {
            if (
              firstHtmlImg.startsWith("http://") ||
              firstHtmlImg.startsWith("https://") ||
              firstHtmlImg.startsWith("data:")
            ) {
              resolvedImage = firstHtmlImg
            } else {
              try {
                // Resolving relative to index/root
                const slugStr = typeof file.data.slug === "string" ? file.data.slug : ""
                const resolved = new URL(firstHtmlImg, "https://base.com/" + slugStr)
                resolvedImage = "." + decodeURIComponent(resolved.pathname)
              } catch {
                resolvedImage = firstHtmlImg
              }
            }
          }

          const explicitMode = (file.data as any).explicitCoverMode
          let finalCoverMode: "frame" | "image" = "frame"

          if (explicitMode === "frame") {
            finalCoverMode = "frame"
          } else if (explicitMode === "image") {
            finalCoverMode = resolvedImage ? "image" : "frame"
          } else {
            // Default: if an image exists in the note, default to image; otherwise frame
            finalCoverMode = resolvedImage ? "image" : "frame"
          }

          ;(file.data as any).coverMode = finalCoverMode
          ;(file.data as any).coverImage = resolvedImage || ""
          fm.cover_mode = finalCoverMode
          fm.cover = resolvedImage || ""
          fm.portfolio_cover = finalCoverMode === "frame" ? "frame" : (resolvedImage || "image")
        },
      ]
    },
  }
}



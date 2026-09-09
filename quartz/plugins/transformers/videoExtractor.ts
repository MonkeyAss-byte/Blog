import { QuartzTransformerPlugin } from "../types"

export const VideoExtractor: QuartzTransformerPlugin = () => {
  return {
    name: "VideoExtractor",
    markdownPlugins() {
      return [
        () => (tree, file) => {
          const content = String(file.value || "")
          const fm = (file.data.frontmatter as Record<string, any>) ?? {}
          file.data.frontmatter = fm

          const slug = file.data.slug || ""
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

          // Video Extraction:
          // 1. From frontmatter (portfolio_video or video)
          let videoUrl = fm.portfolio_video || fm.video

          // 2. If not specified, scan markdown body for <video ... data-src="..."> or src="..."
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
        },
      ]
    },
  }
}

import { FullSlug, resolveRelative } from "../util/path"
import { QuartzPluginData } from "../plugins/vfile"
import { getDate } from "./Date"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"

export interface PortfolioItem {
  slug: FullSlug
  title: string
  date?: Date
  dateStr?: string
  description: string
  video?: string
  cover?: string
  order: number
}

function formatDate(date: Date | undefined): string {
  if (!date) return ""
  try {
    const y = date.getFullYear()
    const m = String(date.getMonth() + 1).padStart(2, "0")
    const d = String(date.getDate()).padStart(2, "0")
    return `${y}.${m}.${d}`
  } catch {
    return ""
  }
}

export default (() => {
  const PortfolioShowcase: QuartzComponent = ({ fileData, allFiles }: QuartzComponentProps) => {
    const isHome = fileData.slug === "index"

    // If on a note page (non-index), render the floating return pill
    if (!isHome) {
      const isPortfolioNote =
        fileData.frontmatter?.portfolio === true ||
        fileData.frontmatter?.portfolio === "true" ||
        fileData.slug?.startsWith("Portfolio/")

      return (
        <div
          id="portfolio-floating-nav"
          class="portfolio-floating-nav"
          data-is-portfolio={isPortfolioNote ? "true" : "false"}
        >
          <a
            href={resolveRelative(fileData.slug!, "index" as FullSlug) + "#portfolio-showcase"}
            class="portfolio-floating-btn"
            title="返回主页作品集"
            data-router-link="true"
          >
            <span class="portfolio-floating-icon">
              <svg
                viewBox="0 0 24 24"
                width="18"
                height="18"
                fill="none"
                stroke="currentColor"
                stroke-width="2.2"
                stroke-linecap="round"
                stroke-linejoin="round"
              >
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
                <polyline points="9 22 9 12 15 12 15 22"></polyline>
              </svg>
            </span>
            <span class="portfolio-floating-text">返回主页作品集</span>
          </a>
        </div>
      )
    }

    // On index page: extract all portfolio items
    const portfolioFiles = (allFiles || []).filter((file: QuartzPluginData) => {
      if (file.slug === "index") return false
      const fm = file.frontmatter as Record<string, any> | undefined
      if (!fm) return false

      if (fm.portfolio === false || fm.portfolio === "false") return false
      if (fm.portfolio === true || fm.portfolio === "true") return true

      const tags = Array.isArray(fm.tags) ? fm.tags : []
      if (
        tags.some(
          (t: any) =>
            typeof t === "string" &&
            (t.toLowerCase() === "portfolio" || t === "作品集"),
        )
      ) {
        return true
      }

      return false
    })

    if (portfolioFiles.length === 0) {
      return null
    }

    // Map to normalized items
    const items: PortfolioItem[] = portfolioFiles.map((file) => {
      const fm = (file.frontmatter as Record<string, any>) ?? {}
      const fileDate = getDate(file)
      const order = Number(fm.portfolio_order ?? 999)
      const video = fm.video || (file as any).video || ""
      const cover = fm.portfolio_cover || fm.cover || ""
      const desc = fm.description || (file as any).description || ""
      const title = fm.title || file.slug?.split("/").pop() || "未命名作品"

      return {
        slug: file.slug as FullSlug,
        title,
        date: fileDate,
        dateStr: formatDate(fileDate),
        description: desc,
        video,
        cover,
        order,
      }
    })

    // Sort: primary by order ascending, secondary by date descending
    items.sort((a, b) => {
      if (a.order !== b.order) {
        return a.order - b.order
      }
      const timeA = a.date ? a.date.getTime() : 0
      const timeB = b.date ? b.date.getTime() : 0
      return timeB - timeA
    })

    return (
      <section id="portfolio-showcase" class="portfolio-showcase-section">
        <div class="portfolio-header">
          <div class="portfolio-title-group">
            <div class="portfolio-badge-pill">
              <span class="portfolio-pulse-dot"></span>
              <span>SHOWCASE &amp; DEMOS</span>
            </div>
            <h2 class="portfolio-title">精选作品与技术拆解</h2>
            <p class="portfolio-subtitle">
              实时图形渲染 · Shader 算法 · 引擎管线拆解与工具开发
            </p>
          </div>
        </div>

        <div class="portfolio-grid">
          {items.map((item) => {
            const detailUrl = `${resolveRelative(fileData.slug!, item.slug)}?from=portfolio`

            return (
              <div
                class="portfolio-card"
                data-slug={item.slug}
              >
                {/* Media area */}
                <div class="portfolio-card-media">
                  {item.video ? (
                    <div class="portfolio-video-wrapper">
                      <video
                        playsinline
                        preload="none"
                        muted
                        loop
                        controlsList="nodownload noplaybackrate nopictureinpicture"
                        disablePictureInPicture
                        data-src={item.video}
                        poster={item.cover || undefined}
                      >
                        您的浏览器不支持直接播放视频。
                      </video>
                      <div class="portfolio-video-cover">
                        <div
                          class="portfolio-play-btn"
                          title="点击播放高清演示视频"
                          aria-label="播放视频"
                        >
                          <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
                            <polygon points="7 4 20 12 7 20 7 4"></polygon>
                          </svg>
                        </div>
                        <div class="portfolio-video-badge">
                          <span class="video-dot"></span>
                          <span>DEMO VIDEO</span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div class="portfolio-fallback-banner">
                      <div class="portfolio-fallback-mesh"></div>
                      <div class="portfolio-fallback-icon">
                        <svg
                          viewBox="0 0 24 24"
                          width="36"
                          height="36"
                          fill="none"
                          stroke="currentColor"
                          stroke-width="1.8"
                          stroke-linecap="round"
                          stroke-linejoin="round"
                        >
                          <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                          <polyline points="2 17 12 22 22 17"></polyline>
                          <polyline points="2 12 12 17 22 12"></polyline>
                        </svg>
                      </div>
                      <span class="portfolio-fallback-label">TECHNICAL ARTICLE</span>
                    </div>
                  )}
                </div>

                {/* Content area */}
                <div class="portfolio-card-body">
                  {item.dateStr && (
                    <div class="portfolio-card-meta">
                      <span class="portfolio-card-date">{item.dateStr}</span>
                    </div>
                  )}

                  <h3 class="portfolio-card-title">
                    <a href={detailUrl} class="portfolio-card-title-link">
                      {item.title}
                    </a>
                  </h3>

                  {item.description && (
                    <p class="portfolio-card-desc">{item.description}</p>
                  )}

                  <div class="portfolio-card-footer">
                    <a href={detailUrl} class="portfolio-card-link-btn">
                      <span>阅读拆解</span>
                      <svg
                        viewBox="0 0 24 24"
                        width="16"
                        height="16"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2.2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        class="arrow-icon"
                      >
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                        <polyline points="12 5 19 12 12 19"></polyline>
                      </svg>
                    </a>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </section>
    )
  }

  PortfolioShowcase.displayName = "PortfolioShowcase"
  return PortfolioShowcase
}) satisfies QuartzComponentConstructor

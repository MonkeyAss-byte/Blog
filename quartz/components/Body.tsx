import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"
// @ts-ignore
import fluentScript from "./scripts/fluent.inline"

const Body: QuartzComponent = ({ children }: QuartzComponentProps) => {
  return (
    <div id="quartz-body">
      {children}
    </div>
  )
}

Body.afterDOMLoaded = fluentScript

export default (() => Body) satisfies QuartzComponentConstructor


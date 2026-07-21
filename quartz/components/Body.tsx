import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "./types"
// @ts-ignore
import fluidScript from "./scripts/fluid.inline"

const Body: QuartzComponent = ({ children }: QuartzComponentProps) => {
  return (
    <div id="quartz-body">
      <canvas id="fluid-canvas" style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: -1; pointer-events: none;"></canvas>
      {children}
    </div>
  )
}

Body.afterDOMLoaded = fluidScript

export default (() => Body) satisfies QuartzComponentConstructor


// WebGL Fluid Simulation for background
// Inspired by Pavel Dobryakov's WebGL Fluid Simulation

interface Pointer {
  id: number
  x: number
  y: number
  dx: number
  dy: number
  down: boolean
  color: number[]
}

document.addEventListener("DOMContentLoaded", () => {
  const canvas = document.getElementById("fluid-canvas") as HTMLCanvasElement
  if (!canvas) return

  // Set canvas size
  function resizeCanvas() {
    canvas.width = window.innerWidth
    canvas.height = window.innerHeight
  }
  resizeCanvas()
  window.addEventListener("resize", resizeCanvas)

  const params = {
    SIM_RESOLUTION: 128,
    DYE_RESOLUTION: 512,
    DENSITY_DISSIPATION: 0.97,
    VELOCITY_DISSIPATION: 0.98,
    PRESSURE_DISSIPATION: 0.8,
    PRESSURE_ITERATIONS: 20,
    SPLAT_RADIUS: 0.005,
    SPLAT_FORCE: 6000,
  }

  const gl = canvas.getContext("webgl", {
    alpha: true,
    depth: false,
    stencil: false,
    antialias: false,
    preserveDrawingBuffer: false,
  })

  if (!gl) {
    console.warn("WebGL not supported, fluid simulation background disabled.")
    return
  }

  // Get WebGL extensions
  const halfFloat = gl.getExtension("OES_texture_half_float")
  gl.getExtension("OES_texture_half_float_linear")
  const supportLinearFiltering = gl.getExtension("OES_texture_float_linear")

  const textureType = halfFloat ? halfFloat.HALF_FLOAT_OES : gl.UNSIGNED_BYTE
  const internalFormat = gl.RGBA
  const format = gl.RGBA

  function getGLSLPrecision(): string {
    const format = gl!.getShaderPrecisionFormat(gl!.FRAGMENT_SHADER, gl!.HIGH_FLOAT)
    return format && format.precision > 0 ? "highp" : "mediump"
  }

  const precision = getGLSLPrecision()

  // Helper: Compile Shader
  function compileShader(type: number, source: string): WebGLShader {
    const shader = gl!.createShader(type)!
    gl!.shaderSource(shader, source)
    gl!.compileShader(shader)
    if (!gl!.getShaderParameter(shader, gl!.COMPILE_STATUS)) {
      console.error(gl!.getShaderInfoLog(shader))
    }
    return shader
  }

  // Helper: Create Program
  function createProgram(vertexSource: string, fragmentSource: string): WebGLProgram {
    const vertexShader = compileShader(gl!.VERTEX_SHADER, vertexSource)
    const fragmentShader = compileShader(gl!.FRAGMENT_SHADER, fragmentSource)
    const program = gl!.createProgram()!
    gl!.attachShader(program, vertexShader)
    gl!.attachShader(program, fragmentShader)
    gl!.linkProgram(program)
    if (!gl!.getProgramParameter(program, gl!.LINK_STATUS)) {
      console.error(gl!.getProgramInfoLog(program))
    }
    return program
  }

  // Vertex Shader (common for all passes)
  const baseVertexShader = `
    precision highp float;
    attribute vec2 aPosition;
    varying vec2 vUv;
    varying vec2 vL;
    varying vec2 vR;
    varying vec2 vT;
    varying vec2 vB;
    uniform vec2 texelSize;
    void main () {
      vUv = aPosition * 0.5 + 0.5;
      vL = vUv - vec2(texelSize.x, 0.0);
      vR = vUv + vec2(texelSize.x, 0.0);
      vT = vUv + vec2(0.0, texelSize.y);
      vB = vUv - vec2(0.0, texelSize.y);
      gl_Position = vec4(aPosition, 0.0, 1.0);
    }
  `

  // Fragment Shaders
  const clearShader = `
    precision ${precision} float;
    varying vec2 vUv;
    uniform sampler2D uTexture;
    uniform float value;
    void main () {
      gl_FragColor = value * texture2D(uTexture, vUv);
    }
  `

  const splatShader = `
    precision ${precision} float;
    varying vec2 vUv;
    uniform sampler2D uTarget;
    uniform float aspect;
    uniform vec2 point;
    uniform vec3 color;
    uniform float radius;
    void main () {
      vec2 p = vUv - point.xy;
      p.x *= aspect;
      vec3 splat = exp(-dot(p, p) / radius) * color;
      vec3 base = texture2D(uTarget, vUv).xyz;
      gl_FragColor = vec4(base + splat, 1.0);
    }
  `

  const advectShader = `
    precision ${precision} float;
    varying vec2 vUv;
    uniform sampler2D uVelocity;
    uniform sampler2D uSource;
    uniform vec2 texelSize;
    uniform float dt;
    uniform float dissipation;
    void main () {
      vec2 coord = vUv - dt * texture2D(uVelocity, vUv).xy * texelSize;
      gl_FragColor = dissipation * texture2D(uSource, coord);
    }
  `

  const divergenceShader = `
    precision ${precision} float;
    varying vec2 vUv;
    varying vec2 vL;
    varying vec2 vR;
    varying vec2 vT;
    varying vec2 vB;
    uniform sampler2D uVelocity;
    void main () {
      float L = texture2D(uVelocity, vL).x;
      float R = texture2D(uVelocity, vR).x;
      float T = texture2D(uVelocity, vT).y;
      float B = texture2D(uVelocity, vB).y;
      float div = 0.5 * (R - L + T - B);
      gl_FragColor = vec4(div, 0.0, 0.0, 1.0);
    }
  `

  const pressureShader = `
    precision ${precision} float;
    varying vec2 vUv;
    varying vec2 vL;
    varying vec2 vR;
    varying vec2 vT;
    varying vec2 vB;
    uniform sampler2D uPressure;
    uniform sampler2D uDivergence;
    void main () {
      float L = texture2D(uPressure, vL).x;
      float R = texture2D(uPressure, vR).x;
      float T = texture2D(uPressure, vT).y;
      float B = texture2D(uPressure, vB).y;
      float div = texture2D(uDivergence, vUv).x;
      float p = (L + R + B + T - div) * 0.25;
      gl_FragColor = vec4(p, 0.0, 0.0, 1.0);
    }
  `

  const gradientSubtractShader = `
    precision ${precision} float;
    varying vec2 vUv;
    varying vec2 vL;
    varying vec2 vR;
    varying vec2 vT;
    varying vec2 vB;
    uniform sampler2D uPressure;
    uniform sampler2D uVelocity;
    void main () {
      float L = texture2D(uPressure, vL).x;
      float R = texture2D(uPressure, vR).x;
      float T = texture2D(uPressure, vT).y;
      float B = texture2D(uPressure, vB).y;
      vec2 vel = texture2D(uVelocity, vUv).xy;
      vel -= vec2(R - L, T - B) * 0.5;
      gl_FragColor = vec4(vel, 0.0, 1.0);
    }
  `

  const displayShader = `
    precision ${precision} float;
    varying vec2 vUv;
    uniform sampler2D uDye;
    void main () {
      vec4 c = texture2D(uDye, vUv);
      // Cyberpunk theme glow blend (transparent background)
      gl_FragColor = vec4(c.rgb, c.a * 0.45);
    }
  `

  // Compile programs
  const clearProgram = createProgram(baseVertexShader, clearShader)
  const splatProgram = createProgram(baseVertexShader, splatShader)
  const advectProgram = createProgram(baseVertexShader, advectShader)
  const divergenceProgram = createProgram(baseVertexShader, divergenceShader)
  const pressureProgram = createProgram(baseVertexShader, pressureShader)
  const gradientSubtractProgram = createProgram(baseVertexShader, gradientSubtractShader)
  const displayProgram = createProgram(baseVertexShader, displayShader)

  // Full Screen Quad
  const quadBuffer = gl.createBuffer()
  gl.bindBuffer(gl.ARRAY_BUFFER, quadBuffer)
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]), gl.STATIC_DRAW)

  // Framebuffer objects (FBO)
  interface FBO {
    texture: WebGLTexture
    fbo: WebGLFramebuffer
    width: number
    height: number
    texelSizeX: number
    texelSizeY: number
    attach(id: number): number
  }

  function createFBO(w: number, h: number): FBO {
    gl!.activeTexture(gl!.TEXTURE0)
    const texture = gl!.createTexture()!
    gl!.bindTexture(gl!.TEXTURE_2D, texture)
    gl!.texImage2D(gl!.TEXTURE_2D, 0, internalFormat, w, h, 0, format, textureType, null)
    gl!.texParameteri(gl!.TEXTURE_2D, gl!.TEXTURE_MIN_FILTER, supportLinearFiltering ? gl!.LINEAR : gl!.NEAREST)
    gl!.texParameteri(gl!.TEXTURE_2D, gl!.TEXTURE_MAG_FILTER, supportLinearFiltering ? gl!.LINEAR : gl!.NEAREST)
    gl!.texParameteri(gl!.TEXTURE_2D, gl!.TEXTURE_WRAP_S, gl!.CLAMP_TO_EDGE)
    gl!.texParameteri(gl!.TEXTURE_2D, gl!.TEXTURE_WRAP_T, gl!.CLAMP_TO_EDGE)

    const fbo = gl!.createFramebuffer()!
    gl!.bindFramebuffer(gl!.FRAMEBUFFER, fbo)
    gl!.framebufferTexture2D(gl!.FRAMEBUFFER, gl!.COLOR_ATTACHMENT0, gl!.TEXTURE_2D, texture, 0)

    return {
      texture,
      fbo,
      width: w,
      height: h,
      texelSizeX: 1.0 / w,
      texelSizeY: 1.0 / h,
      attach(id: number) {
        gl!.activeTexture(gl!.TEXTURE0 + id)
        gl!.bindTexture(gl!.TEXTURE_2D, texture)
        return id
      },
    }
  }

  interface DoubleFBO {
    read: FBO
    write: FBO
    swap(): void
  }

  function createDoubleFBO(w: number, h: number): DoubleFBO {
    let read = createFBO(w, h)
    let write = createFBO(w, h)
    return {
      get read() {
        return read
      },
      get write() {
        return write
      },
      swap() {
        const temp = read
        read = write
        write = temp
      },
    }
  }

  // FBO States
  let velocity = createDoubleFBO(params.SIM_RESOLUTION, params.SIM_RESOLUTION)
  let dye = createDoubleFBO(params.DYE_RESOLUTION, params.DYE_RESOLUTION)
  const divergence = createFBO(params.SIM_RESOLUTION, params.SIM_RESOLUTION)
  const pressure = createDoubleFBO(params.SIM_RESOLUTION, params.SIM_RESOLUTION)

  // Interaction Pointers
  const pointers: Pointer[] = []
  
  // Track single pointer for main interaction
  const activePointer: Pointer = {
    id: -1,
    x: 0,
    y: 0,
    dx: 0,
    dy: 0,
    down: false,
    color: [0.0, 1.0, 0.4], // Quantum Phosphor Green
  }
  pointers.push(activePointer)

  // Generate color palette (monochromatic terminal greens)
  function getRandomNeonColor(): number[] {
    const palette = [
      [0.0, 1.0, 0.4],   // Phosphor Green
      [0.0, 0.8, 0.25],  // Matrix Green
      [0.2, 0.9, 0.5],   // Bright Terminal Green
      [0.0, 0.6, 0.15],  // Darker Matrix Green
    ]
    return palette[Math.floor(Math.random() * palette.length)]
  }


  // Event Listeners on WINDOW (global detection, avoids element blocking)
  window.addEventListener("mousedown", (e) => {
    activePointer.down = true
    activePointer.x = e.clientX
    activePointer.y = e.clientY
    activePointer.dx = 0
    activePointer.dy = 0
    activePointer.color = getRandomNeonColor()
  })

  window.addEventListener("mousemove", (e) => {
    if (!activePointer.down) return
    const dx = e.clientX - activePointer.x
    const dy = e.clientY - activePointer.y
    activePointer.dx = dx
    activePointer.dy = dy
    activePointer.x = e.clientX
    activePointer.y = e.clientY
  })

  window.addEventListener("mouseup", () => {
    activePointer.down = false
  })

  // Touch Support
  window.addEventListener("touchstart", (e) => {
    if (e.targetTouches.length === 0) return
    const touch = e.targetTouches[0]
    activePointer.down = true
    activePointer.x = touch.clientX
    activePointer.y = touch.clientY
    activePointer.dx = 0
    activePointer.dy = 0
    activePointer.color = getRandomNeonColor()
  })

  window.addEventListener("touchmove", (e) => {
    if (e.targetTouches.length === 0) return
    const touch = e.targetTouches[0]
    const dx = touch.clientX - activePointer.x
    const dy = touch.clientY - activePointer.y
    activePointer.dx = dx
    activePointer.dy = dy
    activePointer.x = touch.clientX
    activePointer.y = touch.clientY
  })

  window.addEventListener("touchend", () => {
    activePointer.down = false
  })

  // Helpers: Render Passes
  function drawQuad() {
    gl!.bindBuffer(gl!.ARRAY_BUFFER, quadBuffer)
    gl!.vertexAttribPointer(0, 2, gl!.FLOAT, false, 0, 0)
    gl!.enableVertexAttribArray(0)
    gl!.drawArrays(gl!.TRIANGLES, 0, 6)
  }

  // Splatting fluid force
  function splat(x: number, y: number, dx: number, dy: number, color: number[]) {
    gl!.viewport(0, 0, velocity.width, velocity.height)
    gl!.useProgram(splatProgram)
    gl!.uniform1i(gl!.getUniformLocation(splatProgram, "uTarget"), velocity.read.attach(0))
    gl!.uniform1f(gl!.getUniformLocation(splatProgram, "aspect"), canvas.width / canvas.height)
    gl!.uniform2f(gl!.getUniformLocation(splatProgram, "point"), x / canvas.width, 1.0 - y / canvas.height)
    gl!.uniform3f(gl!.getUniformLocation(splatProgram, "color"), dx * params.SPLAT_FORCE, -dy * params.SPLAT_FORCE, 1.0)
    gl!.uniform1f(gl!.getUniformLocation(splatProgram, "radius"), params.SPLAT_RADIUS)
    gl!.bindFramebuffer(gl!.FRAMEBUFFER, velocity.write.fbo)
    drawQuad()
    velocity.swap()

    gl!.viewport(0, 0, dye.width, dye.height)
    gl!.uniform1i(gl!.getUniformLocation(splatProgram, "uTarget"), dye.read.attach(0))
    gl!.uniform3f(gl!.getUniformLocation(splatProgram, "color"), color[0] * 0.7, color[1] * 0.7, color[2] * 0.7)
    gl!.bindFramebuffer(gl!.FRAMEBUFFER, dye.write.fbo)
    drawQuad()
    dye.swap()
  }

  let lastUpdateTime = Date.now()

  // Main Render/Physics Update loop
  function update() {
    const now = Date.now()
    let dt = (now - lastUpdateTime) / 1000
    dt = Math.min(dt, 0.033) // cap frame rate physics
    lastUpdateTime = now

    gl!.disable(gl!.BLEND)

    // 1. Advect velocity
    gl!.viewport(0, 0, velocity.width, velocity.height)
    gl!.useProgram(advectProgram)
    gl!.uniform2f(gl!.getUniformLocation(advectProgram, "texelSize"), velocity.read.texelSizeX, velocity.read.texelSizeY)
    gl!.uniform1i(gl!.getUniformLocation(advectProgram, "uVelocity"), velocity.read.attach(0))
    gl!.uniform1i(gl!.getUniformLocation(advectProgram, "uSource"), velocity.read.attach(0))
    gl!.uniform1f(gl!.getUniformLocation(advectProgram, "dt"), dt)
    gl!.uniform1f(gl!.getUniformLocation(advectProgram, "dissipation"), params.VELOCITY_DISSIPATION)
    gl!.bindFramebuffer(gl!.FRAMEBUFFER, velocity.write.fbo)
    drawQuad()
    velocity.swap()

    // 2. Advect dye (color density)
    gl!.viewport(0, 0, dye.width, dye.height)
    gl!.uniform2f(gl!.getUniformLocation(advectProgram, "texelSize"), dye.read.texelSizeX, dye.read.texelSizeY)
    gl!.uniform1i(gl!.getUniformLocation(advectProgram, "uVelocity"), velocity.read.attach(0))
    gl!.uniform1i(gl!.getUniformLocation(advectProgram, "uSource"), dye.read.attach(1))
    gl!.uniform1f(gl!.getUniformLocation(advectProgram, "dissipation"), params.DENSITY_DISSIPATION)
    gl!.bindFramebuffer(gl!.FRAMEBUFFER, dye.write.fbo)
    drawQuad()
    dye.swap()

    // 3. Apply Pointer Splats
    for (const pointer of pointers) {
      if (pointer.down && (Math.abs(pointer.dx) > 0.1 || Math.abs(pointer.dy) > 0.1)) {
        splat(pointer.x, pointer.y, pointer.dx, pointer.dy, pointer.color)
        pointer.dx *= 0.8
        pointer.dy *= 0.8
      }
    }

    // 4. Calculate Divergence
    gl!.viewport(0, 0, divergence.width, divergence.height)
    gl!.useProgram(divergenceProgram)
    gl!.uniform2f(gl!.getUniformLocation(divergenceProgram, "texelSize"), divergence.texelSizeX, divergence.texelSizeY)
    gl!.uniform1i(gl!.getUniformLocation(divergenceProgram, "uVelocity"), velocity.read.attach(0))
    gl!.bindFramebuffer(gl!.FRAMEBUFFER, divergence.fbo)
    drawQuad()

    // 5. Clear pressure
    gl!.viewport(0, 0, pressure.width, pressure.height)
    gl!.useProgram(clearProgram)
    gl!.uniform1i(gl!.getUniformLocation(clearProgram, "uTexture"), pressure.read.attach(0))
    gl!.uniform1f(gl!.getUniformLocation(clearProgram, "value"), params.PRESSURE_DISSIPATION)
    gl!.bindFramebuffer(gl!.FRAMEBUFFER, pressure.write.fbo)
    drawQuad()
    pressure.swap()

    // 6. Jacobi pressure solver iterations
    gl!.useProgram(pressureProgram)
    gl!.uniform2f(gl!.getUniformLocation(pressureProgram, "texelSize"), pressure.read.texelSizeX, pressure.read.texelSizeY)
    gl!.uniform1i(gl!.getUniformLocation(pressureProgram, "uDivergence"), divergence.attach(0))
    for (let i = 0; i < params.PRESSURE_ITERATIONS; i++) {
      gl!.uniform1i(gl!.getUniformLocation(pressureProgram, "uPressure"), pressure.read.attach(1))
      gl!.bindFramebuffer(gl!.FRAMEBUFFER, pressure.write.fbo)
      drawQuad()
      pressure.swap()
    }

    // 7. Subtract pressure gradient from velocity to enforce incompressibility
    gl!.viewport(0, 0, velocity.width, velocity.height)
    gl!.useProgram(gradientSubtractProgram)
    gl!.uniform2f(gl!.getUniformLocation(gradientSubtractProgram, "texelSize"), velocity.read.texelSizeX, velocity.read.texelSizeY)
    gl!.uniform1i(gl!.getUniformLocation(gradientSubtractProgram, "uPressure"), pressure.read.attach(0))
    gl!.uniform1i(gl!.getUniformLocation(gradientSubtractProgram, "uVelocity"), velocity.read.attach(1))
    gl!.bindFramebuffer(gl!.FRAMEBUFFER, velocity.write.fbo)
    drawQuad()
    velocity.swap()

    // 8. Render to screen
    gl!.viewport(0, 0, canvas.width, canvas.height)
    gl!.bindFramebuffer(gl!.FRAMEBUFFER, null)
    gl!.clearColor(0, 0, 0, 0)
    gl!.clear(gl!.COLOR_BUFFER_BIT)
    gl!.useProgram(displayProgram)
    gl!.uniform1i(gl!.getUniformLocation(displayProgram, "uDye"), dye.read.attach(0))
    drawQuad()

    requestAnimationFrame(update)
  }

  // Start loop
  requestAnimationFrame(update)
})

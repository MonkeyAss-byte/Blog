import fs from "fs"
import path from "path"
import YAML from "yaml"
import { installPlugins, parsePluginSource } from "./gitLoader.js"

const CONFIG_YAML_PATH = path.join(process.cwd(), "quartz.config.yaml")
const DEFAULT_CONFIG_YAML_PATH = path.join(process.cwd(), "quartz.config.default.yaml")

function readConfig() {
  const configPath = fs.existsSync(CONFIG_YAML_PATH) ? CONFIG_YAML_PATH : DEFAULT_CONFIG_YAML_PATH
  if (!fs.existsSync(configPath)) {
    return {}
  }
  const raw = fs.readFileSync(configPath, "utf-8")
  return YAML.parse(raw)
}

async function main() {
  const quartzConfig: any = readConfig()

  const externalPlugins = quartzConfig.externalPlugins || []

  if (externalPlugins.length === 0) {
    console.log("No external plugins to install.")
    return
  }

  console.log(`Installing ${externalPlugins.length} plugin(s) from Git...`)

  const specs = externalPlugins.map((source: string) => parsePluginSource(source))
  const installed = await installPlugins(specs, { verbose: true })

  if (installed.size === externalPlugins.length) {
    console.log("✓ All plugins installed successfully")
  } else {
    console.error(`✗ Only ${installed.size}/${externalPlugins.length} plugins installed`)
    process.exit(1)
  }
}

main().catch((err) => {
  console.error("Failed to install plugins:", err)
  process.exit(1)
})

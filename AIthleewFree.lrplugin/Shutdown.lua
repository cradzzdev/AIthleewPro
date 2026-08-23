--[[
    AIthleewPro - Shutdown Handler
    Called when Lightroom shuts down or the plugin is unloaded.
]]

local LrPathUtils = import "LrPathUtils"
local pluginDir = (_PLUGIN and _PLUGIN.path) or LrPathUtils.child(LrPathUtils.getStandardFilePath("appData"), "Modules/AIthleewPro.lrplugin")
if not LrPathUtils.isAbsolute(pluginDir) or not LrPathUtils.child(pluginDir, "Info.lua") then
    local fallback = LrPathUtils.child(LrPathUtils.getStandardFilePath("appData"), "Modules/AutoColorPro.lrplugin")
    if LrPathUtils.isAbsolute(fallback) then pluginDir = fallback end
end

local function loadModule(modulePath)
    local fullPath = LrPathUtils.child(pluginDir, modulePath)
    local chunk, err = loadfile(fullPath)
    if chunk then return chunk() else error("Failed to load: " .. modulePath .. " - " .. tostring(err)) end
end

local Logger = loadModule("Utils/Logger.lua")
local logger = Logger:getLogger("Shutdown")

logger:info("Shutting down AIthleewPro")

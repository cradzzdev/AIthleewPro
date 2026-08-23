--[[
    AIthleewPro - Tether Menu Entry Point
    Khởi chạy giao diện Tether FTP từ menu Lightroom Classic.
]]

local LrTasks = import "LrTasks"
local LrFunctionContext = import "LrFunctionContext"
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

local TetherPanel = loadModule("UI/TetherPanel.lua")

LrTasks.startAsyncTask(function()
    LrFunctionContext.callWithContext("AIthleewPro_Tether", function(context)
        TetherPanel:show(context)
    end)
end)


--[[
    AIthleewFree - Main Entry Point
    Lightroom Classic Plugin for Automatic Color Adjustment (Free Edition)
]]

local LrApplication = import "LrApplication"
local LrDialogs = import "LrDialogs"
local LrFunctionContext = import "LrFunctionContext"
local LrLogger = import "LrLogger"
local LrPathUtils = import "LrPathUtils"
local LrTasks = import "LrTasks"
local LrView = import "LrView"

local pluginDir = (_PLUGIN and _PLUGIN.path) or LrPathUtils.child(LrPathUtils.getStandardFilePath("appData"), "Modules/AIthleewFree.lrplugin")
if not LrPathUtils.isAbsolute(pluginDir) or not LrPathUtils.child(pluginDir, "Info.lua") then
    local fallback = LrPathUtils.child(LrPathUtils.getStandardFilePath("appData"), "Modules/AutoColorFree.lrplugin")
    if LrPathUtils.isAbsolute(fallback) then pluginDir = fallback end
end

local function loadModule(modulePath)
    local fullPath = LrPathUtils.child(pluginDir, modulePath)
    local chunk, err = loadfile(fullPath)
    if chunk then
        return chunk()
    else
        error("Failed to load module: " .. modulePath .. " - " .. tostring(err))
    end
end

local Logger = loadModule("Utils/Logger.lua")
local Config = loadModule("Utils/Config.lua")
local TaskRunner = loadModule("Bridge/TaskRunner.lua")
local Panel = loadModule("UI/Panel.lua")

local logger = Logger:getLogger("Main")

local PLUGIN_NAME = "AIthleewFree"
local PLUGIN_VERSION = "1.0.0"

local function initialize()
    logger:info("Initializing " .. PLUGIN_NAME .. " v" .. PLUGIN_VERSION)

    Config:load()

    local task_runner = TaskRunner:new({
        python_path = Config:get("python_path"),
    })

    if not task_runner:ensure_process_running() then
        logger:error("Failed to start Python AI engine")
        return false, nil
    end

    logger:info(PLUGIN_NAME .. " initialized successfully")
    return true, task_runner
end

LrTasks.startAsyncTask(function()
    LrFunctionContext.callWithContext("AIthleewFree", function(context)
        local ok, task_runner = initialize()

        if not ok then
            LrDialogs.showError("Không thể khởi chạy AIthleewFree. Vui lòng kiểm tra file nhật ký (log).")
            return
        end

        local catalog = LrApplication.activeCatalog()
        local target_photo = catalog:getTargetPhoto()

        if target_photo == nil then
            LrDialogs.message("Chưa chọn bức ảnh nào", "Vui lòng chọn một hoặc nhiều bức ảnh trong thư viện Lightroom để phân tích.")
            return
        end

        logger:info("Mở bảng điều khiển AIthleewFree")
        Panel:show(context, task_runner)
    end)
end)


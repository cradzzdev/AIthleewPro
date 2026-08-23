--[[
    AIthleewPro - Analyzer Core
    High-level analysis interface that coordinates between UI and AI engine.
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
local Export = loadModule("Utils/Export.lua")
local Adjuster = loadModule("Core/Adjuster.lua")

local logger = Logger:getLogger("Analyzer")

local Analyzer = {}
Analyzer.__index = Analyzer

function Analyzer:new(task_runner)
    local obj = {
        task_runner = task_runner,
        export = Export:new(),
        adjuster = Adjuster:new(),
        current_result = nil,
    }
    setmetatable(obj, self)
    return obj
end

function Analyzer:analyze_photo(photo, options)
    if not photo then
        return nil, "no photo"
    end

    options = options or {}

    local preview_path = self.export:exportPhoto(photo, {
        max_dimension = options.preview_size or 1024,
        quality = 85,
    })

    if not preview_path then
        return nil, "Failed to export preview"
    end

    local result = nil
    local err = nil

    result, err = self.task_runner:analyze(preview_path, {
        mode = options.mode or "full",
        use_cloud = options.use_cloud,
        scene_hint = options.scene_hint,
    })

    self.export:cleanup({ preview_path })

    if result then
        self.current_result = result
        return result
    end

    return nil, err
end

function Analyzer:apply_to_photo(photo)
    if not self.current_result then
        return false, "No analysis result available"
    end

    local adjustments = self.current_result.adjustments
    if not adjustments then
        return false, "No adjustments in result"
    end

    return self.adjuster:apply(photo, adjustments)
end

function Analyzer:apply_to_photos(photos, progress_callback)
    if not self.current_result then
        return false, "No analysis result available"
    end

    local adjustments = self.current_result.adjustments
    if not adjustments then
        return false, "No adjustments in result"
    end

    return self.adjuster:applyBatch(photos, adjustments, progress_callback)
end

function Analyzer:get_current_result()
    return self.current_result
end

function Analyzer:clear_result()
    self.current_result = nil
end

return Analyzer

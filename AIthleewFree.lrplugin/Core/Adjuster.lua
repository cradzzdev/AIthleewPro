--[[
    AIthleewFree - Develop Settings Adjuster
    Applies basic tone and neutral white balance adjustments to Lightroom develop settings.
    Free Edition limits: Basic Tone (Exposure, Contrast, Highlights, Shadows, Whites, Blacks, Temp, Tint, Vibrance, Saturation).
    Effects, Color Grading, HSL Channels, AI Masking, and Advanced Presence are restricted to Pro.
]]

local LrApplication = import "LrApplication"
local LrTasks = import "LrTasks"
local LrDialogs = import "LrDialogs"
local LrPathUtils = import "LrPathUtils"

local pluginDir = (_PLUGIN and _PLUGIN.path) or LrPathUtils.child(LrPathUtils.getStandardFilePath("appData"), "Modules/AIthleewFree.lrplugin")
if not LrPathUtils.isAbsolute(pluginDir) or not LrPathUtils.child(pluginDir, "Info.lua") then
    local fallback = LrPathUtils.child(LrPathUtils.getStandardFilePath("appData"), "Modules/AutoColorFree.lrplugin")
    if LrPathUtils.isAbsolute(fallback) then pluginDir = fallback end
end
local function loadModule(modulePath)
    local fullPath = LrPathUtils.child(pluginDir, modulePath)
    local chunk, err = loadfile(fullPath)
    if chunk then return chunk() else error("Failed to load: " .. modulePath .. " - " .. tostring(err)) end
end

local Logger = loadModule("Utils/Logger.lua")
local FormatHelper = loadModule("Utils/FormatHelper.lua")
local Config = loadModule("Utils/Config.lua")
local logger = Logger:getLogger("Adjuster")

local Adjuster = {}
Adjuster.__index = Adjuster

function Adjuster:new()
    local obj = {}
    setmetatable(obj, self)
    return obj
end

function Adjuster:buildSettings(adjustments, photo)
    if not adjustments then return nil, 0 end

    local settings = {}
    local count = 0

    -- Process Version
    settings.ProcessVersion = "15.4"

    -- White Balance (Temperature & Tint)
    local isRaw = false
    if photo then
        isRaw = FormatHelper.isRawPhoto(photo)
    end
    if adjustments.is_raw ~= nil then
        isRaw = adjustments.is_raw
    end

    if (adjustments.temperature ~= nil or adjustments.tint ~= nil or adjustments.target_kelvin ~= nil or adjustments.relative_temp ~= nil or adjustments.wb ~= nil) then
        settings.WhiteBalance = "Custom"

        local tempVal = adjustments.temperature
        local tintVal = adjustments.tint

        if adjustments.wb and type(adjustments.wb) == "table" then
            tempVal = adjustments.wb.temperature or adjustments.wb.target_kelvin or adjustments.wb.relative_temp or tempVal
            tintVal = adjustments.wb.tint or adjustments.wb.target_tint or adjustments.wb.relative_tint or tintVal
        end

        if isRaw then
            -- RAW files: Kelvin 2,000 to 50,000
            if tempVal ~= nil then
                local k = tonumber(tempVal) or 5500
                if k < 2000 then k = 2000 end
                if k > 50000 then k = 50000 end
                settings.Temperature = math.floor(k + 0.5)
                count = count + 1
            end
            if tintVal ~= nil then
                local t = tonumber(tintVal) or 0
                if t < -150 then t = -150 end
                if t > 150 then t = 150 end
                settings.Tint = math.floor(t + 0.5)
                count = count + 1
            end
        else
            -- Non-RAW files (JPEG/TIFF/PNG): Relative shift -100 to +100
            if tempVal ~= nil then
                local s = tonumber(tempVal) or 0
                if s < -100 then s = -100 end
                if s > 100 then s = 100 end
                local finalTemp = math.floor(s + 0.5)
                settings.IncrementalTemperature = finalTemp
                count = count + 1
            end
            if tintVal ~= nil then
                local t = tonumber(tintVal) or 0
                if t < -100 then t = -100 end
                if t > 100 then t = 100 end
                local finalTint = math.floor(t + 0.5)
                settings.IncrementalTint = finalTint
                count = count + 1
            end
        end
    end

    -- Basic Tone sliders
    local function clamp(val, min_v, max_v)
        if not val then return nil end
        val = tonumber(val)
        if not val then return nil end
        if val < min_v then val = min_v end
        if val > max_v then val = max_v end
        return val
    end

    local function clampInt(val, min_v, max_v)
        local c = clamp(val, min_v, max_v)
        return c and math.floor(c + 0.5) or nil
    end

    if adjustments.exposure ~= nil then
        settings.Exposure2012 = clamp(adjustments.exposure, -5.0, 5.0)
        count = count + 1
    end

    if adjustments.contrast ~= nil then
        settings.Contrast2012 = clampInt(adjustments.contrast, -100, 100)
        count = count + 1
    end

    if adjustments.highlights ~= nil then
        settings.Highlights2012 = clampInt(adjustments.highlights, -100, 100)
        count = count + 1
    end

    if adjustments.shadows ~= nil then
        settings.Shadows2012 = clampInt(adjustments.shadows, -100, 100)
        count = count + 1
    end

    if adjustments.whites ~= nil then
        settings.Whites2012 = clampInt(adjustments.whites, -100, 100)
        count = count + 1
    end

    if adjustments.blacks ~= nil then
        settings.Blacks2012 = clampInt(adjustments.blacks, -100, 100)
        count = count + 1
    end

    -- Presence (Vibrance & Saturation only in Free)
    if adjustments.vibrance ~= nil then
        settings.Vibrance = clampInt(adjustments.vibrance, -100, 100)
        count = count + 1
    end

    if adjustments.saturation ~= nil then
        settings.Saturation = clampInt(adjustments.saturation, -100, 100)
        count = count + 1
    end

    return settings, count
end

function Adjuster:applyColors(photo, adjustments, history_label)
    if not photo then
        logger:error("applyColors called with nil photo")
        return false, "no photo"
    end

    local globalSettings, count = self:buildSettings(adjustments, photo)
    if not globalSettings or count == 0 then
        return false, "no adjustments to apply"
    end

    local catalog = LrApplication.activeCatalog()
    local histName = history_label or "AIthleewFree AI"

    local function execute()
        local ok, err = LrTasks.pcall(function()
            catalog:withWriteAccessDo(histName, function(context)
                photo:applyDevelopSettings(globalSettings)
            end)
        end)

        if ok then
            pcall(function()
                local LrDevelopController = import "LrDevelopController"
                if LrDevelopController and type(LrDevelopController.setValue) == "function" then
                    for k, v in pairs(globalSettings) do
                        if k ~= "ProcessVersion" and k ~= "WhiteBalance" then
                            pcall(function()
                                LrDevelopController.setValue(k, v)
                            end)
                        end
                    end
                end
            end)
            logger:info(string.format("AIthleewFree: Applied color adjustments to: %s", photo:getFormattedMetadata("fileName")))
            return true
        else
            logger:error("AIthleewFree: applyDevelopSettings failed: " .. tostring(err))
            return false, tostring(err)
        end
    end

    if LrTasks.canYield() then
        return execute()
    else
        LrTasks.startAsyncTask(function()
            execute()
        end)
        return true
    end
end

function Adjuster:apply(photo, adjustments, history_label)
    return self:applyColors(photo, adjustments, history_label)
end

return Adjuster

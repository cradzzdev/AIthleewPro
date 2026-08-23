--[[
    AIthleewPro - Preset Manager
    Manages plugin presets for different scene types.
]]

local LrApplication = import "LrApplication"
local LrPathUtils = import "LrPathUtils"
local LrFileUtils = import "LrFileUtils"

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
local Json = loadModule("Utils/Json.lua")

local logger = Logger:getLogger("PresetManager")

local PresetManager = {}
PresetManager.__index = PresetManager

local PRESET_CATEGORIES = {
    "portraits",
    "landscapes",
    "night",
    "food",
    "product",
    "macro",
    "street",
    "architecture",
    "custom",
}

local initialized = false
local presetBaseDir = nil

function PresetManager:new()
    local obj = {
        presets = {},
    }
    setmetatable(obj, self)
    obj:ensureInit()
    return obj
end

function PresetManager:ensureInit()
    if initialized then return end

    local lrConfigPath = LrPathUtils.getStandardFilePath("appData")
    presetBaseDir = LrPathUtils.child(lrConfigPath, "AIthleewPro/presets")
    local oldBaseDir = LrPathUtils.child(lrConfigPath, "AutoColorPro/presets")
    if not LrFileUtils.exists(presetBaseDir) and LrFileUtils.exists(oldBaseDir) then
        presetBaseDir = oldBaseDir
    end

    LrFileUtils.createAllDirectories(presetBaseDir)
    for _, category in ipairs(PRESET_CATEGORIES) do
        local cat_dir = LrPathUtils.child(presetBaseDir, category)
        LrFileUtils.createAllDirectories(cat_dir)
    end

    initialized = true
    logger:info("Preset manager initialized at: " .. presetBaseDir)
end

function PresetManager:getCategories()
    return PRESET_CATEGORIES
end

function PresetManager:getPresets(category)
    local cat_dir = LrPathUtils.child(presetBaseDir, category or "all")

    local presets = {}

    if not LrFileUtils.exists(cat_dir) then
        return presets
    end

    for file in LrFileUtils.childFiles(cat_dir) do
        local ext = LrPathUtils.extension(file)
        if ext == "json" or ext == "lrtemplate" then
            table.insert(presets, file)
        end
    end

    return presets
end

function PresetManager:loadPreset(preset_path)
    if not preset_path or not LrFileUtils.exists(preset_path) then
        return nil
    end

    local ext = LrPathUtils.extension(preset_path)
    local content = LrFileUtils.readFile(preset_path)
    if not content then return nil end

    if ext == "json" then
        return Json.decode(content)
    end

    local env = { s = nil }
    local chunk, err = loadstring(content)
    if not chunk then
        logger:error("Failed to load preset: " .. tostring(err))
        return nil
    end

    setfenv(chunk, env)
    local success = pcall(chunk)
    if success and type(env.s) == "table" then
        return env.s
    end

    logger:error("Invalid preset format: " .. preset_path)
    return nil
end

function PresetManager:savePreset(name, category, settings)
    if not name or name == "" then return false end

    category = category or "custom"

    local safeName = name:gsub("[^%w%-_ ]", "_")
    local cat_dir = LrPathUtils.child(presetBaseDir, category)
    LrFileUtils.createAllDirectories(cat_dir)

    local preset_path = LrPathUtils.child(cat_dir, safeName .. ".json")
    local json_str = Json.encode(settings)

    local file = io.open(preset_path, "w")
    if not file then
        logger:error("Failed to save preset: " .. preset_path)
        return false
    end

    file:write(json_str)
    file:close()

    logger:info("Preset saved: " .. preset_path)
    return true
end

function PresetManager:deletePreset(preset_path)
    if preset_path and LrFileUtils.exists(preset_path) then
        LrFileUtils.delete(preset_path)
        logger:info("Preset deleted: " .. preset_path)
    end
end

function PresetManager:getDefaultPreset(scene_type)
    local defaults = {
        portraits = {
            Temperature = 5600, Tint = 5, Exposure2012 = 0.1,
            Contrast2012 = 5, Highlights2012 = -15, Shadows2012 = 10,
            Vibrance = 8, Clarity2012 = 10,
        },
        landscapes = {
            Temperature = 5400, Tint = 0, Exposure2012 = 0,
            Contrast2012 = 15, Highlights2012 = -20, Shadows2012 = 15,
            Vibrance = 15, Clarity2012 = 20, Dehaze = 5,
        },
        night = {
            Temperature = 5000, Tint = -5, Exposure2012 = 0.3,
            Contrast2012 = 10, Highlights2012 = -30, Shadows2012 = 25,
            Vibrance = 5, Clarity2012 = -5,
        },
        food = {
            Temperature = 5800, Tint = 5, Exposure2012 = 0.2,
            Contrast2012 = 10, Highlights2012 = -10, Shadows2012 = 5,
            Vibrance = 20, Saturation = 10, Clarity2012 = 15,
        },
        product = {
            Temperature = 5500, Tint = 0, Exposure2012 = 0.1,
            Contrast2012 = 20, Highlights2012 = -15, Shadows2012 = 10,
            Vibrance = 5, Saturation = -5, Clarity2012 = 25,
        },
    }

    return defaults[scene_type]
end

return PresetManager

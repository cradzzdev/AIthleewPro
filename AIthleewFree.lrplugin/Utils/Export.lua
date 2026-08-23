--[[
    AIthleewPro - Image Export Utility
    Exports thumbnails/previews for AI analysis.
]]

local LrApplication = import "LrApplication"
local LrPathUtils = import "LrPathUtils"
local LrFileUtils = import "LrFileUtils"
local LrTasks = import "LrTasks"
local LrExportSession = import "LrExportSession"

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
local Config = loadModule("Utils/Config.lua")

local logger = Logger:getLogger("Export")

local Export = {}
Export.__index = Export

local DEFAULT_EXPORT_FORMAT = "JPEG"
local DEFAULT_QUALITY = 85
local DEFAULT_MAX_DIMENSION = 1024

local fileCounter = 0

function Export:new()
    local obj = {}
    setmetatable(obj, self)
    return obj
end

function Export:getTempPath(suffix)
    suffix = suffix or ".jpg"
    local temp_dir = LrPathUtils.getStandardFilePath("temp")
    fileCounter = fileCounter + 1
    local filename = string.format("aithleew_%d_%d%s", os.time(), fileCounter, suffix)
    return LrPathUtils.child(temp_dir, filename)
end

function Export:exportPhoto(photo, options)
    if not photo then
        logger:error("exportPhoto called with nil photo")
        return nil
    end

    options = options or {}
    local max_dim = options.max_dimension or Config:get("preview_size") or DEFAULT_MAX_DIMENSION
    local quality = options.quality or DEFAULT_QUALITY

    local fileName = photo:getFormattedMetadata("fileName") or "unknown"
    logger:debug("Exporting photo: " .. fileName)

    local temp_dir = LrPathUtils.getStandardFilePath("temp")

    local export_settings = {
        LR_format = "JPEG",
        LR_jpeg_quality = quality > 1 and (quality / 100) or quality,
        LR_size_doConstrain = true,
        LR_size_maxWidth = max_dim,
        LR_size_maxHeight = max_dim,
        LR_size_resizeType = "longEdge",
        LR_removeMetadata = true,
        LR_export_destinationType = "specificFolder",
        LR_export_destinationPathPrefix = temp_dir,
        LR_export_useSubfolder = false,
        LR_collisionHandling = "rename",
        LR_reimportExportedPhoto = false,
    }

    local session = LrExportSession({
        photosToExport = { photo },
        exportSettings = export_settings,
    })

    for _, rendition in session:renditions() do
        local success, pathOrMessage = rendition:waitForRender()
        if success and pathOrMessage and LrFileUtils.exists(pathOrMessage) then
            logger:debug("Photo exported to: " .. pathOrMessage)
            return pathOrMessage
        else
            logger:error("Export rendition failed: " .. tostring(pathOrMessage))
        end
    end

    logger:error("Failed to export photo: " .. fileName)
    return nil
end

function Export:exportPhotos(photos, options)
    if not photos or #photos == 0 then
        logger:warn("exportPhotos called with empty list")
        return {}
    end

    local exported_paths = {}

    for _, photo in ipairs(photos) do
        local path = self:exportPhoto(photo, options)
        if path then
            table.insert(exported_paths, path)
        end
    end

    return exported_paths
end

function Export:cleanup(paths)
    if not paths then return end
    for _, path in ipairs(paths) do
        if path and LrFileUtils.exists(path) then
            LrFileUtils.delete(path)
            logger:debug("Cleaned up: " .. path)
        end
    end
end

return Export

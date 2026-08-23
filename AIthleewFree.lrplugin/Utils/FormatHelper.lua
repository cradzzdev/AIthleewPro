--[[
    AIthleewPro - Format Helper
    Comprehensive camera RAW and rendered file format detection across all manufacturers.
    Supports all uppercase and lowercase prefixes/extensions.
]]

local LrPathUtils = import "LrPathUtils"

local FormatHelper = {}

-- Comprehensive list of RAW formats in UPPERCASE
FormatHelper.RAW_LIST = {
    -- Sony
    "ARW", "SRF", "SR2", "BAY",
    -- Canon
    "CR2", "CR3", "CRW",
    -- Nikon
    "NEF", "NRW",
    -- Fujifilm
    "RAF",
    -- Olympus / OM System
    "ORF", "ORI",
    -- Panasonic / Lumix
    "RW2",
    -- Leica
    "RWL", "RAW",
    -- Hasselblad
    "3FR", "FFF",
    -- Phase One / Leaf / Mamiya
    "IIQ", "CAP", "EIP", "MOS", "MEF",
    -- Pentax / Ricoh
    "PEF", "PTX",
    -- Sigma
    "X3F",
    -- Samsung
    "SRW",
    -- Kodak
    "DCR", "KDC", "K25", "DCS", "DRF",
    -- Epson
    "ERF",
    -- Minolta / Konica Minolta
    "MRW", "MDC",
    -- Adobe / Apple ProRAW / DJI / GoPro
    "DNG", "GPR",
    -- Cinema RAW / Generic
    "R3D", "BRAW", "ARI", "CINE"
}

-- Fast lookup map containing UPPERCASE, lowercase, with and without leading dot
FormatHelper.RAW_MAP = {}
for _, ext in ipairs(FormatHelper.RAW_LIST) do
    local u = string.upper(ext)
    local l = string.lower(ext)
    FormatHelper.RAW_MAP[u] = true
    FormatHelper.RAW_MAP[l] = true
    FormatHelper.RAW_MAP["." .. u] = true
    FormatHelper.RAW_MAP["." .. l] = true
end

-- Rendered / Non-RAW map
FormatHelper.RENDERED_MAP = {
    ["JPG"] = true, ["jpg"] = true, [".JPG"] = true, [".jpg"] = true,
    ["JPEG"] = true, ["jpeg"] = true, [".JPEG"] = true, [".jpeg"] = true,
    ["JPE"] = true, ["jpe"] = true,
    ["TIF"] = true, ["tif"] = true, [".TIF"] = true, [".tif"] = true,
    ["TIFF"] = true, ["tiff"] = true, [".TIFF"] = true, [".tiff"] = true,
    ["PNG"] = true, ["png"] = true, [".PNG"] = true, [".png"] = true,
    ["PSD"] = true, ["psd"] = true, [".PSD"] = true, [".psd"] = true,
    ["HEIC"] = true, ["heic"] = true,
    ["HEIF"] = true, ["heif"] = true,
    ["AVIF"] = true, ["avif"] = true,
    ["WEBP"] = true, ["webp"] = true,
}

local function cleanExt(str)
    if not str or type(str) ~= "string" or str == "" then return "" end
    local ext = string.match(str, "%.([^%.\\/]+)$")
    if not ext or ext == "" then
        ext = str
    end
    ext = string.gsub(ext, "^%.", "")
    ext = string.gsub(ext, "%s+", "")
    return string.upper(ext)
end

function FormatHelper.getFileExtension(photo)
    if not photo then return "" end

    -- 1. Check formatted fileName (e.g. "DSC01234.ARW")
    local okName, name = pcall(function() return photo:getFormattedMetadata("fileName") end)
    if okName and name and type(name) == "string" and name ~= "" then
        local ext = cleanExt(name)
        if ext ~= "" and ext ~= string.upper(name) then
            return ext
        end
    end

    -- 2. Check raw metadata path
    local okPath, path = pcall(function() return photo:getRawMetadata("path") end)
    if okPath and path and type(path) == "string" and path ~= "" then
        local ext = cleanExt(path)
        if ext ~= "" and ext ~= string.upper(path) then
            return ext
        end
    end

    -- 3. Virtual copy fallback
    local okVC, isVC = pcall(function() return photo:getRawMetadata("isVirtualCopy") end)
    if okVC and isVC then
        local okMaster, master = pcall(function() return photo:getRawMetadata("masterPhoto") end)
        if okMaster and master then
            return FormatHelper.getFileExtension(master)
        end
    end

    return ""
end

function FormatHelper.isRawPhoto(photo)
    if not photo then return false, "JPG" end

    -- Get filename and path strings for direct pattern matching
    local fileName = ""
    local filePath = ""
    local okName, name = pcall(function() return photo:getFormattedMetadata("fileName") end)
    if okName and name and type(name) == "string" then fileName = string.upper(name) end

    local okPath, path = pcall(function() return photo:getRawMetadata("path") end)
    if okPath and path and type(path) == "string" then filePath = string.upper(path) end

    -- 1. Direct regex scan against all RAW extensions in RAW_LIST
    for _, rawExt in ipairs(FormatHelper.RAW_LIST) do
        local pattern = "%." .. rawExt .. "$"
        if fileName:match(pattern) or filePath:match(pattern) or fileName:find("%." .. rawExt) or filePath:find("%." .. rawExt) then
            return true, rawExt
        end
    end

    -- 2. Check extracted extension in RAW_MAP
    local ext = FormatHelper.getFileExtension(photo)
    if ext ~= "" and FormatHelper.RAW_MAP[ext] then
        return true, ext
    end

    -- 3. Check Lightroom SDK fileFormat
    local okFmt, fmt = pcall(function() return photo:getRawMetadata("fileFormat") end)
    if okFmt and fmt then
        local u = string.upper(tostring(fmt))
        if u == "RAW" or u == "DNG" or FormatHelper.RAW_MAP[u] then
            return true, ext ~= "" and ext or u
        end
        if FormatHelper.RENDERED_MAP[u] then
            return false, ext ~= "" and ext or u
        end
    end

    -- 4. Check formatted fileType (e.g. "Sony ARW raw", "Canon CR3 raw")
    local okType, ftype = pcall(function() return photo:getFormattedMetadata("fileType") end)
    if okType and ftype then
        local fu = string.upper(tostring(ftype))
        for _, rawExt in ipairs(FormatHelper.RAW_LIST) do
            if fu:find(rawExt) then
                return true, rawExt
            end
        end
        if fu:find("RAW") or fu:find("DNG") then
            return true, ext ~= "" and ext or "RAW"
        end
    end

    -- 5. If rendered extension
    if ext ~= "" and FormatHelper.RENDERED_MAP[ext] then
        return false, ext
    end

    return false, ext ~= "" and ext or "JPG"
end

return FormatHelper

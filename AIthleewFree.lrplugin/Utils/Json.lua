--[[
    AIthleewPro - JSON Encoder/Decoder
    Pure Lua JSON library (dkjson compatible)
    No external dependencies, safe for Lightroom Lua 5.1 sandbox
]]

local Json = {}

local escape_char_map = {
    ["\\"] = "\\\\",
    ['"'] = '\\"',
    ["\b"] = "\\b",
    ["\f"] = "\\f",
    ["\n"] = "\\n",
    ["\r"] = "\\r",
    ["\t"] = "\\t",
}

local function escape_char(c)
    return escape_char_map[c] or string.format("\\u%04x", c:byte())
end

local function encode_nil()
    return "null"
end

local function encode_string(s)
    return '"' .. s:gsub('[%z\1-\31\\"]', escape_char) .. '"'
end

local function encode_number(n)
    if n ~= n or n >= math.huge or n <= -math.huge then
        error("Invalid number in JSON: " .. tostring(n))
    end
    return string.format("%.14g", n)
end

local function encode_boolean(b)
    return b and "true" or "false"
end

local function encode_table(t, is_array)
    local parts = {}
    if is_array then
        for _, v in ipairs(t) do
            table.insert(parts, Json.encode(v))
        end
        return "[" .. table.concat(parts, ",") .. "]"
    else
        for k, v in pairs(t) do
            table.insert(parts, Json.encode(tostring(k)) .. ":" .. Json.encode(v))
        end
        return "{" .. table.concat(parts, ",") .. "}"
    end
end

function Json.encode(obj)
    local t = type(obj)
    if t == "nil" then
        return encode_nil()
    elseif t == "string" then
        return encode_string(obj)
    elseif t == "number" then
        return encode_number(obj)
    elseif t == "boolean" then
        return encode_boolean(obj)
    elseif t == "table" then
        local is_array = (#obj > 0)
        if not is_array then
            for k, _ in pairs(obj) do
                if type(k) ~= "string" then
                    is_array = false
                    break
                end
            end
        end
        return encode_table(obj, is_array)
    else
        return '"' .. tostring(obj) .. '"'
    end
end

local function skip_whitespace(str, pos)
    while pos <= #str do
        local c = str:sub(pos, pos)
        if c == " " or c == "\t" or c == "\n" or c == "\r" then
            pos = pos + 1
        else
            break
        end
    end
    return pos
end

local function decode_error(str, pos, msg)
    error(string.format("JSON decode error at %d: %s", pos, msg))
end

local function utf8_char(code)
    if code < 128 then
        return string.char(code)
    elseif code < 2048 then
        return string.char(192 + math.floor(code / 64), 128 + (code % 64))
    elseif code < 65536 then
        return string.char(224 + math.floor(code / 4096), 128 + (math.floor(code / 64) % 64), 128 + (code % 64))
    elseif code < 1114112 then
        return string.char(240 + math.floor(code / 262144), 128 + (math.floor(code / 4096) % 64), 128 + (math.floor(code / 64) % 64), 128 + (code % 64))
    end
    return ""
end

local function unescape_string(s)
    if not s or s == "" then return "" end
    -- Decode \uXXXX unicode escapes
    s = s:gsub("\\u([0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F])", function(hex)
        local code = tonumber(hex, 16)
        return utf8_char(code)
    end)
    -- Decode standard escapes
    s = s:gsub('\\"', '"')
         :gsub("\\\\", "\\")
         :gsub("\\/", "/")
         :gsub("\\b", "\b")
         :gsub("\\f", "\f")
         :gsub("\\n", "\n")
         :gsub("\\r", "\r")
         :gsub("\\t", "\t")
    return s
end

local function parse_string(str, pos)
    pos = pos + 1
    local start = pos
    while pos <= #str do
        local c = str:sub(pos, pos)
        if c == '"' then
            local raw = str:sub(start, pos - 1)
            return unescape_string(raw), pos + 1
        elseif c == "\\" then
            pos = pos + 2
        else
            pos = pos + 1
        end
    end
    return decode_error(str, pos, "unterminated string")
end

local function parse_number(str, pos)
    local start = pos
    if str:sub(pos, pos) == "-" then pos = pos + 1 end
    while pos <= #str and str:sub(pos, pos):match("%d") do pos = pos + 1 end
    if str:sub(pos, pos) == "." then
        pos = pos + 1
        while pos <= #str and str:sub(pos, pos):match("%d") do pos = pos + 1 end
    end
    if str:sub(pos, pos) == "e" or str:sub(pos, pos) == "E" then
        pos = pos + 1
        if str:sub(pos, pos) == "+" or str:sub(pos, pos) == "-" then pos = pos + 1 end
        while pos <= #str and str:sub(pos, pos):match("%d") do pos = pos + 1 end
    end
    local num_str = str:sub(start, pos - 1)
    local num = tonumber(num_str)
    if not num then
        decode_error(str, start, "invalid number: " .. num_str)
    end
    return num, pos
end

local function parse_literal(str, pos, literal, value)
    if str:sub(pos, pos + #literal - 1) == literal then
        return value, pos + #literal
    end
    decode_error(str, pos, "expected " .. literal)
end

local function parse_array(str, pos)
    pos = pos + 1
    local arr = {}
    pos = skip_whitespace(str, pos)
    if str:sub(pos, pos) == "]" then return arr, pos + 1 end
    while true do
        local val
        val, pos = Json.decode_value(str, pos)
        table.insert(arr, val)
        pos = skip_whitespace(str, pos)
        local c = str:sub(pos, pos)
        if c == "]" then return arr, pos + 1 end
        if c ~= "," then decode_error(str, pos, "expected ] or ,") end
        pos = pos + 1
    end
end

local function parse_object(str, pos)
    pos = pos + 1
    local obj = {}
    pos = skip_whitespace(str, pos)
    if str:sub(pos, pos) == "}" then return obj, pos + 1 end
    while true do
        pos = skip_whitespace(str, pos)
        if str:sub(pos, pos) ~= '"' then decode_error(str, pos, "expected string key") end
        local key
        key, pos = parse_string(str, pos)
        pos = skip_whitespace(str, pos)
        if str:sub(pos, pos) ~= ":" then decode_error(str, pos, "expected :") end
        pos = pos + 1
        pos = skip_whitespace(str, pos)
        local val
        val, pos = Json.decode_value(str, pos)
        obj[key] = val
        pos = skip_whitespace(str, pos)
        local c = str:sub(pos, pos)
        if c == "}" then return obj, pos + 1 end
        if c ~= "," then decode_error(str, pos, "expected } or ,") end
        pos = pos + 1
    end
end

function Json.decode_value(str, pos)
    pos = skip_whitespace(str, pos)
    local c = str:sub(pos, pos)
    if c == '"' then
        return parse_string(str, pos)
    elseif c == "{" then
        return parse_object(str, pos)
    elseif c == "[" then
        return parse_array(str, pos)
    elseif c == "t" then
        return parse_literal(str, pos, "true", true)
    elseif c == "f" then
        return parse_literal(str, pos, "false", false)
    elseif c == "n" then
        return parse_literal(str, pos, "null", nil)
    elseif c == "-" or c:match("%d") then
        return parse_number(str, pos)
    else
        decode_error(str, pos, "unexpected character: " .. c)
    end
end

function Json.decode(str)
    if not str or str == "" then return nil end
    local success, result = pcall(function()
        local val, pos = Json.decode_value(str, 1)
        return val
    end)
    if success then
        return result
    else
        return nil
    end
end

return Json

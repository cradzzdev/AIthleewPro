--[[
    AIthleewFree - Plugin Info
    This file is required by Lightroom SDK for plugin initialization.
    Free Edition: 3 Menu Items (AI Auto Color Basic, Tether 1-Hour Trial, Settings).
]]

return {
    LrSdkVersion = 13.0,
    LrSdkMinimumVersion = 10.0,
    LrPluginName = "AIthleewFree",
    LrPluginInfoUrl = "https://github.com/cradzz/AIthleewFree",
    LrPluginAuthor = "AIthleew Team",
    LrPluginVersion = "1.0.0",
    LrToolkitIdentifier = "com.aithleewfree.lightroom.toolkit",
    LrPluginInfoProvider = "PluginManagerProvider.lua",

    LrLibraryMenuItems = {
        {
            title = "AIthleewFree - ⚡ Phân tích & Chỉnh màu AI (Basic)",
            file = "Main.lua",
        },
        {
            title = "AIthleewFree - 📡 Tether (FTP) — Dùng thử 1 tiếng...",
            file = "TetherMenu.lua",
        },
        {
            title = "AIthleewFree - ⚙️ Cài đặt hệ thống (Free)",
            file = "SettingsWrapper.lua",
        },
    },

    LrPluginMenuItems = {
        {
            title = "AIthleewFree - ⚡ Phân tích & Chỉnh màu AI (Basic)",
            file = "Main.lua",
        },
        {
            title = "AIthleewFree - 📡 Tether (FTP) — Dùng thử 1 tiếng...",
            file = "TetherMenu.lua",
        },
        {
            title = "AIthleewFree - ⚙️ Cài đặt hệ thống (Free)",
            file = "SettingsWrapper.lua",
        },
    },

    LrShutdownPlugin = "Shutdown.lua",

    LrForceInitPlugin = true,

    VERSION = {
        major = 1,
        minor = 0,
        revision = 0,
        build = 20260824,
        edition = "free",
    },
}

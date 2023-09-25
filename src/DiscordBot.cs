using DSharpPlus;
using DSharpPlus.CommandsNext;
using DSharpPlus.SlashCommands;

namespace DiscordBot; 

/// <summary>
/// The main discord bot
/// </summary>
public class DiscordBot {
    public DiscordClient DiscordClient { get; private set; }
    public CommandsNextExtension CommandsExtension { get; private set; }
    public SlashCommandsExtension SlashCommandsExtension { get; private set; }
    public SettingsConf Conf { get; private set; }
    public string Version { get; private set; }
    
    /// <summary>
    /// Starts the discord bot
    /// </summary>
    public async Task RunBotAsync() {
        var settingsConfLoader = new SettingsConfLoader();
        settingsConfLoader.LoadConfigSync();
        Conf = settingsConfLoader.SettingsConf;
    }
}
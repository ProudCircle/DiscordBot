using DiscordBot.HypixelApi;
using Newtonsoft.Json;

class Program {
    static void Main(string[] args) {
        Console.WriteLine("[WARNING] - This repo is still under development!\n" +
                          "[WARNING] - Features will NOT work as intended, nor will anything else!\n" +
                          "[WARNING] - YOU HAVE BEEN WARNED");
        
        var jsonString = "{ \"success\": true}";
        var response = JsonConvert.DeserializeObject<HypixelPlayerResponse>(jsonString);
        Console.Out.WriteLine(String.Format("Player has '{0}' bedwars wins!", response.Stats.BedwarsStats.Wins));

        var bot = new DiscordBot.DiscordBot();
        bot.RunBotAsync().GetAwaiter().GetResult();
        Console.Out.WriteLine("Bot is logging off");
    }
}


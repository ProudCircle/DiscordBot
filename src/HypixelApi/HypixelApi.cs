using Newtonsoft.Json;

namespace DiscordBot.HypixelApi;

public class HypixelApi {
    private String _apiKey;
    private int rateLimitRemaining;
    private int rateLimitResetSeconds;

    public HypixelApi(String key) {
        _apiKey = key;
    }

    public async Task<HypixelPlayerResponse> GetPlayer(Guid UUID) {
        var uriBuilder = new HypixelApiEndpointBuilder();
        uriBuilder.Default();
        uriBuilder.SetPlayer(UUID);
        Uri uri = new Uri(uriBuilder.Build());
        using (HttpClient client = new HttpClient()) {
            client.DefaultRequestHeaders.Add("API-Key", _apiKey);
            HttpResponseMessage responseMessage = await client.GetAsync(uri);
            if (responseMessage.IsSuccessStatusCode) {
                string jsonResponse = await responseMessage.Content.ReadAsStringAsync();
                HypixelPlayerResponse player = JsonConvert.DeserializeObject<HypixelPlayerResponse>(jsonResponse);

                if (responseMessage.Headers.TryGetValues("ratelimit-remaining", out var remainingValues)) {
                    if (int.TryParse(remainingValues.FirstOrDefault(), out int remaining)) {
                        rateLimitRemaining = remaining;
                    }
                }

                if (responseMessage.Headers.TryGetValues("ratelimit-reset", out var resetValues)) {
                    if (int.TryParse(resetValues.FirstOrDefault(), out int reset)) {
                        rateLimitResetSeconds = reset;
                    }
                }

                return player;
            }
        }

        rateLimitRemaining = 0;
        rateLimitResetSeconds = -1;

        return new HypixelPlayerResponse();
    }
}
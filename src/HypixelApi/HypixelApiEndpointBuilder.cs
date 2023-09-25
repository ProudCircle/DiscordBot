public class HypixelApiEndpointBuilder {
    private String _prebuiltString = String.Empty;
    private String _defaultUri = "https://api.hypixel.net/";

    public void Default() {
        _prebuiltString = _defaultUri;
    }

    public void SetPlayer(Guid UUID) {
        _prebuiltString = _prebuiltString + "/player?uuid" + UUID;
    }


    public String Build() {
        if (_prebuiltString == _defaultUri) {
            string message = "NullReference to endpoint location (did you forget to select the endpoint?)"
            throw new UriFormatException(message);
        }

        return _prebuiltString;
    }
}

import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  final String baseUrl = "http://127.0.0.1:5000";

  Future<Map<String, dynamic>> signup(String username, String password, String category) async {
    final response = await http.post(
      Uri.parse("$baseUrl/signup"),
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({
        "username": username,
        "password": password,
        "category": category
      }),
    );
    return jsonDecode(response.body);
  }

  Future<Map<String, dynamic>> login(String username, String password) async {
    final response = await http.post(
      Uri.parse("$baseUrl/login"),
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({
        "username": username,
        "password": password
      }),
    );
    return jsonDecode(response.body);
  }

  Future<Map<String, dynamic>> getAqi(int index, String username) async {
    final response = await http.post(
      Uri.parse("$baseUrl/predict/$index"),
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({"username": username}),
    );
    return jsonDecode(response.body);
  }
}

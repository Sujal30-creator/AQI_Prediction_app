import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'predictionpage.dart'; // Import Prediction Page

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  // ignore: library_private_types_in_public_api
  _LoginPageState createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final TextEditingController _usernameController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();
  String? _errorMessage;
  bool _isLoading = false; // Show loading indicator

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black87,
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(20.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.cloud, size: 80, color: Colors.white), // Cloud icon
              const SizedBox(height: 20),

              // Username Input
              TextField(
                controller: _usernameController,
                style: const TextStyle(color: Colors.white),
                decoration: InputDecoration(
                  labelText: "Username",
                  labelStyle: const TextStyle(color: Colors.white),
                  prefixIcon: const Icon(Icons.person, color: Colors.white),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10),
                    borderSide: const BorderSide(color: Colors.white),
                  ),
                ),
              ),
              const SizedBox(height: 15),

              // Password Input
              TextField(
                controller: _passwordController,
                obscureText: true,
                style: const TextStyle(color: Colors.white),
                decoration: InputDecoration(
                  labelText: "Password",
                  labelStyle: const TextStyle(color: Colors.white),
                  prefixIcon: const Icon(Icons.lock, color: Colors.white),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10),
                    borderSide: const BorderSide(color: Colors.white),
                  ),
                ),
              ),
              const SizedBox(height: 20),

              // Login Button with Inline Function
              _isLoading
                  ? const CircularProgressIndicator() // Show loading spinner
                  : ElevatedButton(
                onPressed: () async {
                  setState(() {
                    _errorMessage = null; // Reset error message
                    _isLoading = true; // Show loading indicator
                  });

                  final String username = _usernameController.text.trim();
                  final String password = _passwordController.text.trim();

                  if (username.isEmpty || password.isEmpty) {
                    setState(() {
                      _errorMessage = "❌ Username and password cannot be empty!";
                      _isLoading = false;
                    });
                    return;
                  }

                  try {
                    final response = await http.post(
                      Uri.parse('http://10.0.2.2:5000/login'),
                      headers: {'Content-Type': 'application/json'},
                      body: jsonEncode({'username': username, 'password': password}),
                    );

                    print("🔵 Login API Response: ${response.body}"); // Debug log

                    final responseData = jsonDecode(response.body);

                    if (response.statusCode == 200 && responseData['status'] == 'success') {
                      if (responseData.containsKey('username')) {
                        String loggedInUser = responseData['username']; // ✅ Extract username

                        // ignore: use_build_context_synchronously
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text("✅ Login Successful!"),
                            backgroundColor: Colors.green,
                          ),
                        );

                        Navigator.pushReplacement(
                          // ignore: use_build_context_synchronously
                          context,
                          MaterialPageRoute(
                            builder: (context) => PredictionPage(loggedInUser: loggedInUser),
                          ),
                        );
                      } else {
                        setState(() {
                          _errorMessage = "❌ Unexpected response format: Username missing";
                        });
                      }
                    } else {
                      setState(() {
                        _errorMessage = "❌ Invalid username or password";
                      });
                    }
                  } catch (e) {
                    setState(() {
                      _errorMessage = "❌ Network error: Unable to connect to server";
                    });
                    print("🔴 Login Error: $e"); // Debug log
                  }

                  setState(() {
                    _isLoading = false; // Hide loading indicator
                  });
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.deepPurpleAccent,
                  padding: const EdgeInsets.symmetric(horizontal: 50, vertical: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                ),
                child: const Text("Login", style: TextStyle(fontSize: 16)),
              ),

              if (_errorMessage != null) ...[
                const SizedBox(height: 10),
                Text(
                  _errorMessage!,
                  style: const TextStyle(color: Colors.red, fontWeight: FontWeight.bold),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
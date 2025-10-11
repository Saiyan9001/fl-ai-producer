"""
Tests for Ollama admin/management methods.

Tests model management features including:
- Listing local models
- Pulling models with streaming progress
- Showing running models
- Getting version information
"""
import pytest
from unittest.mock import Mock, patch
from controller_app.ai.providers.ollama_provider import OllamaProvider


class TestOllamaAdmin:
    """Tests for Ollama admin methods."""
    
    @patch("controller_app.ai.providers.ollama_provider._REQUESTS_AVAILABLE", True)
    @patch("controller_app.ai.providers.ollama_provider.requests")
    def test_list_models_success(self, mock_requests):
        """Test successful model listing."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "models": [
                {
                    "name": "llama3.1:latest",
                    "size": 4700000000,
                    "modified_at": "2024-01-15T10:30:00Z"
                },
                {
                    "name": "mistral:latest",
                    "size": 4100000000,
                    "modified_at": "2024-01-14T15:20:00Z"
                }
            ]
        }
        mock_requests.get.return_value = mock_response
        
        provider = OllamaProvider()
        models = provider.list_models()
        
        assert len(models) == 2
        assert models[0]["name"] == "llama3.1:latest"
        assert models[0]["size"] == 4700000000
        assert models[1]["name"] == "mistral:latest"
        
        # Verify API call
        mock_requests.get.assert_called_once()
        call_url = mock_requests.get.call_args[0][0]
        assert call_url.endswith("/api/tags")
    
    @patch("controller_app.ai.providers.ollama_provider._REQUESTS_AVAILABLE", True)
    @patch("controller_app.ai.providers.ollama_provider.requests")
    def test_list_models_empty(self, mock_requests):
        """Test listing models when none are available."""
        mock_response = Mock()
        mock_response.json.return_value = {"models": []}
        mock_requests.get.return_value = mock_response
        
        provider = OllamaProvider()
        models = provider.list_models()
        
        assert len(models) == 0
    
    @patch("controller_app.ai.providers.ollama_provider._REQUESTS_AVAILABLE", True)
    @patch("controller_app.ai.providers.ollama_provider.requests")
    def test_list_models_connection_error(self, mock_requests):
        """Test error handling when connection fails."""
        mock_requests.get.side_effect = Exception("Connection refused")
        
        provider = OllamaProvider()
        
        with pytest.raises(RuntimeError) as exc_info:
            provider.list_models()
        
        assert "Failed to list models" in str(exc_info.value)
    
    @patch("controller_app.ai.providers.ollama_provider._REQUESTS_AVAILABLE", True)
    @patch("controller_app.ai.providers.ollama_provider.requests")
    def test_pull_model_success(self, mock_requests):
        """Test successful model pull with streaming progress."""
        # Mock streaming response
        mock_response = Mock()
        progress_data = [
            b'{"status": "pulling manifest", "completed": 0, "total": 1000}\n',
            b'{"status": "downloading", "completed": 500, "total": 1000}\n',
            b'{"status": "downloading", "completed": 1000, "total": 1000}\n',
            b'{"status": "success"}\n',
        ]
        mock_response.iter_lines.return_value = progress_data
        mock_requests.post.return_value = mock_response
        
        provider = OllamaProvider()
        progress_updates = list(provider.pull_model("llama3.1"))
        
        assert len(progress_updates) == 4
        assert progress_updates[0]["status"] == "pulling manifest"
        assert progress_updates[1]["completed"] == 500
        assert progress_updates[2]["completed"] == 1000
        assert progress_updates[3]["status"] == "success"
        
        # Verify API call
        mock_requests.post.assert_called_once()
        call_url = mock_requests.post.call_args[0][0]
        assert call_url.endswith("/api/pull")
        call_payload = mock_requests.post.call_args[1]["json"]
        assert call_payload["name"] == "llama3.1"
    
    @patch("controller_app.ai.providers.ollama_provider._REQUESTS_AVAILABLE", True)
    @patch("controller_app.ai.providers.ollama_provider.requests")
    def test_pull_model_with_error(self, mock_requests):
        """Test pull model with error in stream."""
        mock_response = Mock()
        progress_data = [
            b'{"status": "pulling manifest"}\n',
            b'{"error": "model not found"}\n',
        ]
        mock_response.iter_lines.return_value = progress_data
        mock_requests.post.return_value = mock_response
        
        provider = OllamaProvider()
        progress_updates = list(provider.pull_model("nonexistent"))
        
        # Should stop on error
        assert len(progress_updates) == 2
        assert "error" in progress_updates[1]
    
    @patch("controller_app.ai.providers.ollama_provider._REQUESTS_AVAILABLE", True)
    @patch("controller_app.ai.providers.ollama_provider.requests")
    def test_pull_model_invalid_json(self, mock_requests):
        """Test pull model handles invalid JSON in stream."""
        mock_response = Mock()
        progress_data = [
            b'{"status": "pulling"}\n',
            b'invalid json\n',
            b'{"status": "success"}\n',
        ]
        mock_response.iter_lines.return_value = progress_data
        mock_requests.post.return_value = mock_response
        
        provider = OllamaProvider()
        progress_updates = list(provider.pull_model("llama3.1"))
        
        # Should skip invalid JSON
        assert len(progress_updates) == 2
        assert progress_updates[0]["status"] == "pulling"
        assert progress_updates[1]["status"] == "success"
    
    @patch("controller_app.ai.providers.ollama_provider._REQUESTS_AVAILABLE", True)
    @patch("controller_app.ai.providers.ollama_provider.requests")
    def test_pull_model_connection_error(self, mock_requests):
        """Test error handling when pull connection fails."""
        mock_requests.post.side_effect = Exception("Connection error")
        
        provider = OllamaProvider()
        
        with pytest.raises(RuntimeError) as exc_info:
            list(provider.pull_model("llama3.1"))
        
        assert "Failed to pull model" in str(exc_info.value)
        assert "llama3.1" in str(exc_info.value)
    
    @patch("controller_app.ai.providers.ollama_provider._REQUESTS_AVAILABLE", True)
    @patch("controller_app.ai.providers.ollama_provider.requests")
    def test_show_running_success(self, mock_requests):
        """Test showing running models."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "models": [
                {
                    "name": "llama3.1:latest",
                    "size": 4700000000,
                    "digest": "abc123"
                }
            ]
        }
        mock_requests.get.return_value = mock_response
        
        provider = OllamaProvider()
        running = provider.show_running()
        
        assert len(running) == 1
        assert running[0]["name"] == "llama3.1:latest"
        
        # Verify API call
        mock_requests.get.assert_called_once()
        call_url = mock_requests.get.call_args[0][0]
        assert call_url.endswith("/api/ps")
    
    @patch("controller_app.ai.providers.ollama_provider._REQUESTS_AVAILABLE", True)
    @patch("controller_app.ai.providers.ollama_provider.requests")
    def test_show_running_empty(self, mock_requests):
        """Test showing running models when none are running."""
        mock_response = Mock()
        mock_response.json.return_value = {"models": []}
        mock_requests.get.return_value = mock_response
        
        provider = OllamaProvider()
        running = provider.show_running()
        
        assert len(running) == 0
    
    @patch("controller_app.ai.providers.ollama_provider._REQUESTS_AVAILABLE", True)
    @patch("controller_app.ai.providers.ollama_provider.requests")
    def test_show_running_error(self, mock_requests):
        """Test error handling when getting running models fails."""
        mock_requests.get.side_effect = Exception("Connection error")
        
        provider = OllamaProvider()
        
        with pytest.raises(RuntimeError) as exc_info:
            provider.show_running()
        
        assert "Failed to get running models" in str(exc_info.value)
    
    @patch("controller_app.ai.providers.ollama_provider._REQUESTS_AVAILABLE", True)
    @patch("controller_app.ai.providers.ollama_provider.requests")
    def test_show_version_success(self, mock_requests):
        """Test getting Ollama version."""
        mock_response = Mock()
        mock_response.json.return_value = {"version": "0.1.26"}
        mock_requests.get.return_value = mock_response
        
        provider = OllamaProvider()
        version = provider.show_version()
        
        assert version == "0.1.26"
        
        # Verify API call
        mock_requests.get.assert_called_once()
        call_url = mock_requests.get.call_args[0][0]
        assert call_url.endswith("/api/version")
    
    @patch("controller_app.ai.providers.ollama_provider._REQUESTS_AVAILABLE", True)
    @patch("controller_app.ai.providers.ollama_provider.requests")
    def test_show_version_missing_field(self, mock_requests):
        """Test getting version when field is missing."""
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_requests.get.return_value = mock_response
        
        provider = OllamaProvider()
        version = provider.show_version()
        
        assert version == "unknown"
    
    @patch("controller_app.ai.providers.ollama_provider._REQUESTS_AVAILABLE", True)
    @patch("controller_app.ai.providers.ollama_provider.requests")
    def test_show_version_error(self, mock_requests):
        """Test error handling when getting version fails."""
        mock_requests.get.side_effect = Exception("Connection error")
        
        provider = OllamaProvider()
        
        with pytest.raises(RuntimeError) as exc_info:
            provider.show_version()
        
        assert "Failed to get Ollama version" in str(exc_info.value)
    
    @patch("controller_app.ai.providers.ollama_provider._REQUESTS_AVAILABLE", False)
    def test_admin_methods_no_requests_library(self):
        """Test error when requests library is not available."""
        provider = OllamaProvider()
        
        with pytest.raises(RuntimeError) as exc_info:
            provider.list_models()
        assert "requests" in str(exc_info.value).lower()
        
        with pytest.raises(RuntimeError) as exc_info:
            list(provider.pull_model("test"))
        assert "requests" in str(exc_info.value).lower()
        
        with pytest.raises(RuntimeError) as exc_info:
            provider.show_running()
        assert "requests" in str(exc_info.value).lower()
        
        with pytest.raises(RuntimeError) as exc_info:
            provider.show_version()
        assert "requests" in str(exc_info.value).lower()

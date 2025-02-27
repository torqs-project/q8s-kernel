import unittest
from unittest.mock import patch, MagicMock
from kubernetes import client
from q8s.plugins.job_template_spec import CPUJobTemplatePlugin, CUDAJobTemplatePlugin
from q8s.enums import Target


class TestCPUandGPUJobTemplatePlugin(unittest.TestCase):

    @patch("q8s.plugins.job_template_spec.client.V1Container")
    @patch("q8s.plugins.job_template_spec.client.V1PodTemplateSpec")
    @patch("q8s.plugins.job_template_spec.client.V1PodSpec")
    @patch("q8s.plugins.job_template_spec.client.V1ObjectMeta")
    @patch("q8s.plugins.job_template_spec.client.V1VolumeMount")
    @patch("q8s.plugins.job_template_spec.client.V1Volume")
    @patch("q8s.plugins.job_template_spec.client.V1ConfigMapVolumeSource")
    @patch("q8s.plugins.job_template_spec.client.V1LocalObjectReference")
    @patch("q8s.plugins.job_template_spec.client.V1ResourceRequirements")
    def test_makejob_cpu(
        self,
        mock_v1_resource_requirements,
        mock_v1_local_object_reference,
        mock_v1_config_map_volume_source,
        mock_v1_volume,
        mock_v1_volume_mount,
        mock_v1_object_meta,
        mock_v1_pod_spec,
        mock_v1_pod_template_spec,
        mock_v1_container,
    ):
        plugin = CPUJobTemplatePlugin()
        name = "test-job"
        registry_pat = None
        registry_credentials_secret_name = "test-secret"
        container_image = "test-image"
        env = {"TEST_ENV": "value"}
        target = Target.cpu

        result = plugin.makejob(
            name,
            registry_pat,
            registry_credentials_secret_name,
            container_image,
            env,
            target,
        )

        self.assertIsNotNone(result)
        mock_v1_container.assert_called_once()
        mock_v1_pod_template_spec.assert_called_once()
        mock_v1_pod_spec.assert_called_once()
        mock_v1_object_meta.assert_called_once()
        mock_v1_volume_mount.assert_called_once()
        mock_v1_volume.assert_called_once()
        mock_v1_config_map_volume_source.assert_called_once()

    @patch("q8s.plugins.job_template_spec.client.V1Container")
    @patch("q8s.plugins.job_template_spec.client.V1PodTemplateSpec")
    @patch("q8s.plugins.job_template_spec.client.V1PodSpec")
    @patch("q8s.plugins.job_template_spec.client.V1ObjectMeta")
    @patch("q8s.plugins.job_template_spec.client.V1VolumeMount")
    @patch("q8s.plugins.job_template_spec.client.V1Volume")
    @patch("q8s.plugins.job_template_spec.client.V1ConfigMapVolumeSource")
    @patch("q8s.plugins.job_template_spec.client.V1LocalObjectReference")
    @patch("q8s.plugins.job_template_spec.client.V1ResourceRequirements")
    def test_makejob_gpu(
        self,
        mock_v1_resource_requirements,
        mock_v1_local_object_reference,
        mock_v1_config_map_volume_source,
        mock_v1_volume,
        mock_v1_volume_mount,
        mock_v1_object_meta,
        mock_v1_pod_spec,
        mock_v1_pod_template_spec,
        mock_v1_container,
    ):
        plugin = CUDAJobTemplatePlugin()
        name = "test-job"
        registry_pat = "test-pat"
        registry_credentials_secret_name = "test-secret"
        container_image = "test-image"
        env = {"TEST_ENV": "value"}
        target = Target.gpu

        result = plugin.makejob(
            name,
            registry_pat,
            registry_credentials_secret_name,
            container_image,
            env,
            target,
        )

        self.assertIsNotNone(result)
        mock_v1_container.assert_called_once()
        mock_v1_pod_template_spec.assert_called_once()
        mock_v1_pod_spec.assert_called_once()
        mock_v1_object_meta.assert_called_once()
        mock_v1_volume_mount.assert_called_once()
        mock_v1_volume.assert_called_once()
        mock_v1_config_map_volume_source.assert_called_once()
        mock_v1_local_object_reference.assert_called_once()
        mock_v1_resource_requirements.assert_called_once()

    def test_makejob_invalid_target(self):
        plugin = CPUJobTemplatePlugin()
        name = "test-job"
        registry_pat = None
        registry_credentials_secret_name = "test-secret"
        container_image = "test-image"
        env = {"TEST_ENV": "value"}
        target = "invalid-target"

        result = plugin.makejob(
            name,
            registry_pat,
            registry_credentials_secret_name,
            container_image,
            env,
            target,
        )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()

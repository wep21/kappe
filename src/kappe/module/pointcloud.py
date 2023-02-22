import numpy as np
from pydantic import BaseModel, Extra
from scipy.spatial.transform import Rotation

from kappe.utils.pointcloud2 import create_cloud, read_points
from kappe.utils.settings import SettingRotation
from kappe.utils.types import McapROSMessage


class SettingPointCloud(BaseModel, extra=Extra.forbid):
    """
    Point cloud settings.

    :ivar remove_zero: Remove points with all zero coordinates (x, y, z).
    :ivar rotation: Rotation to apply to point cloud.
    :ivar field_mapping: Mapping of point cloud field names to a new name.
    """

    remove_zero: bool = False
    rotation: SettingRotation = SettingRotation()
    field_mapping: dict[str, str] | None


def point_cloud(cfg: SettingPointCloud, msg: McapROSMessage):
    if cfg.field_mapping is not None:
        for pc_field in msg.ros_msg.fields:
            pc_field.name = cfg.field_mapping.get(
                pc_field.name, pc_field.name)

    fields = [x.name for x in msg.ros_msg.fields]
    if 'x' in fields and 'y' in fields and 'z' in fields:
        cloud = np.array(read_points(msg.ros_msg))
        org_len = len(cloud)

        if cfg.remove_zero:
            cloud = cloud[np.logical_and(
                cloud['x'] != 0.0, cloud['y'] != 0.0,
                cloud['z'] != 0.0)]

        quat = cfg.rotation.to_quaternion()
        if quat is not None:
            rot = Rotation.from_quat(np.array(quat))
            stack = np.column_stack([cloud['x'], cloud['y'], cloud['z']])

            r_cloud = rot.apply(stack)

            cloud['x'] = r_cloud[:, 0]
            cloud['y'] = r_cloud[:, 1]
            cloud['z'] = r_cloud[:, 2]

        if quat is not None or len(cloud) != org_len:
            msg_cloud = create_cloud(
                msg.ros_msg.header,
                msg.ros_msg.fields,
                cloud,
                msg.ros_msg.point_step,
            )
            msg.ros_msg.data = msg_cloud['data']

            msg.ros_msg.height = msg_cloud['height']
            msg.ros_msg.width = msg_cloud['width']
            msg.ros_msg.is_dense = msg_cloud['is_dense']
            msg.ros_msg.is_bigendian = msg_cloud['is_bigendian']
            msg.ros_msg.point_step = msg_cloud['point_step']
            msg.ros_msg.row_step = msg_cloud['row_step']
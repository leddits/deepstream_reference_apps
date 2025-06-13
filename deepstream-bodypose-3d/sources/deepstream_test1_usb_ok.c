/*
 * Copyright (c) 2018-2019, NVIDIA CORPORATION. All rights reserved.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a
 * copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
 * DEALINGS IN THE SOFTWARE.
 */

#include <gst/gst.h>
#include <glib.h>
#include <stdio.h>
#include "gstnvdsmeta.h"

#define MAX_DISPLAY_LEN 64

#define PGIE_CLASS_ID_VEHICLE 0
#define PGIE_CLASS_ID_PERSON 2

/* The muxer output resolution must be set if the input streams will be of
 * different resolution. The muxer will scale all the input frames to this
 * resolution. */
#define MUXER_OUTPUT_WIDTH 640
#define MUXER_OUTPUT_HEIGHT 480

/* Muxer batch formation timeout, for e.g. 40 millisec. Should ideally be set
 * based on the fastest source's framerate. */
#define MUXER_BATCH_TIMEOUT_USEC 4000000

//#define NVVIDCONV

gint frame_number = 0;
gchar pgie_classes_str[4][32] = { "Vehicle", "TwoWheeler", "Person",
  "Roadsign"
};

/* osd_sink_pad_buffer_probe  will extract metadata received on OSD sink pad
 * and update params for drawing rectangle, object information etc. */

static GstPadProbeReturn
osd_sink_pad_buffer_probe (GstPad * pad, GstPadProbeInfo * info,
    gpointer u_data)
{
    GstBuffer *buf = (GstBuffer *) info->data;
    guint num_rects = 0; 
    NvDsObjectMeta *obj_meta = NULL;
    guint vehicle_count = 0;
    guint person_count = 0;
    NvDsMetaList * l_frame = NULL;
    NvDsMetaList * l_obj = NULL;
    NvDsDisplayMeta *display_meta = NULL;

    NvDsBatchMeta *batch_meta = gst_buffer_get_nvds_batch_meta (buf);

    for (l_frame = batch_meta->frame_meta_list; l_frame != NULL;
      l_frame = l_frame->next) {
        NvDsFrameMeta *frame_meta = (NvDsFrameMeta *) (l_frame->data);
        int offset = 0;
        for (l_obj = frame_meta->obj_meta_list; l_obj != NULL;
                l_obj = l_obj->next) {
            obj_meta = (NvDsObjectMeta *) (l_obj->data);
            if (obj_meta->class_id == PGIE_CLASS_ID_VEHICLE) {
                vehicle_count++;
                num_rects++;
            }
            if (obj_meta->class_id == PGIE_CLASS_ID_PERSON) {
                person_count++;
                num_rects++;
            }
        }
        display_meta = nvds_acquire_display_meta_from_pool(batch_meta);
        NvOSD_TextParams *txt_params  = &display_meta->text_params[0];
        display_meta->num_labels = 1;
        txt_params->display_text = g_malloc0 (MAX_DISPLAY_LEN);
        offset = snprintf(txt_params->display_text, MAX_DISPLAY_LEN, "Person = %d ", person_count);
        offset = snprintf(txt_params->display_text + offset , MAX_DISPLAY_LEN, "Vehicle = %d ", vehicle_count);

        /* Now set the offsets where the string should appear */
        txt_params->x_offset = 10;
        txt_params->y_offset = 12;

        /* Font , font-color and font-size */
        txt_params->font_params.font_name = "Serif";
        txt_params->font_params.font_size = 10;
        txt_params->font_params.font_color.red = 1.0;
        txt_params->font_params.font_color.green = 1.0;
        txt_params->font_params.font_color.blue = 1.0;
        txt_params->font_params.font_color.alpha = 1.0;

        /* Text background color */
        txt_params->set_bg_clr = 1;
        txt_params->text_bg_clr.red = 0.0;
        txt_params->text_bg_clr.green = 0.0;
        txt_params->text_bg_clr.blue = 0.0;
        txt_params->text_bg_clr.alpha = 1.0;

        nvds_add_display_meta_to_frame(frame_meta, display_meta);
    }

    g_print ("Frame Number = %d Number of objects = %d "
            "Vehicle Count = %d Person Count = %d\n",
            frame_number, num_rects, vehicle_count, person_count);
    frame_number++;
    return GST_PAD_PROBE_OK;
}

static gboolean
bus_call (GstBus * bus, GstMessage * msg, gpointer data)
{
  GMainLoop *loop = (GMainLoop *) data;
  switch (GST_MESSAGE_TYPE (msg)) {
    case GST_MESSAGE_EOS:
      g_print ("End of stream\n");
      g_main_loop_quit (loop);
      break;
    case GST_MESSAGE_ERROR:{
      gchar *debug;
      GError *error;
      gst_message_parse_error (msg, &error, &debug);
      g_printerr ("ERROR from element %s: %s\n",
          GST_OBJECT_NAME (msg->src), error->message);
      if (debug)
        g_printerr ("Error details: %s\n", debug);
      g_free (debug);
      g_error_free (error);
      g_main_loop_quit (loop);
      break;
    }
    default:
      break;
  }
  return TRUE;
}

GstElement* make_element(const gchar* factory_name, const gchar *element_name)
{
    GstElement  *element;
    element = gst_element_factory_make (factory_name, element_name);
    if(!element){
        g_printerr ("%s could not be created. Exiting.\n", factory_name);
        return NULL;
    }
    return element;
}


int
main (int argc, char *argv[])
{
  GMainLoop *loop = NULL;
  GstElement *pipeline = NULL, *source = NULL,
      *streammux = NULL, *sink = NULL, *pgie = NULL, *nvvidconv = NULL,
      *nvosd = NULL;
  GstElement *src_conv = NULL, *nvconv = NULL;
  GstElement *caps_v4l2src = NULL, *caps_vidconvsrc = NULL, *caps_srcconv = NULL;
  GstCaps *caps_uyvy = NULL, *caps_nv12_nvmm = NULL, *caps_nv12 = NULL;
  GstCapsFeatures *feature = NULL;
  GstElement *transform = NULL;
  GstBus *bus = NULL;
  guint bus_watch_id;
  GstPad *osd_sink_pad = NULL;

  /* Standard GStreamer initialization */
  gst_init (&argc, &argv);
  loop = g_main_loop_new (NULL, FALSE);

  /* Create gstreamer elements */
  /* Create Pipeline element that will form a connection of other elements */
  pipeline = gst_pipeline_new ("usb-camara-pipeline");
  if (!pipeline) {
    g_printerr ("One element could not be created. Exiting.\n");
    return -1;
  }

  /* Source element for reading from the file */
  source = make_element("v4l2src", "usb-camera-hahaha");
  caps_v4l2src = make_element("capsfilter", "v4l2src_caps");
  src_conv = make_element ("videoconvert", "src-conv");
  caps_srcconv = make_element("capsfilter", "hubin test");
  nvconv = make_element ("nvvideoconvert", "nvconv");
  caps_vidconvsrc = make_element("capsfilter", "nvmm_caps");
  streammux = make_element ("nvstreammux", "stream-muxer");
  pgie = make_element ("nvinfer", "primary-nvinference-engine");
  nvvidconv = make_element ("nvvideoconvert", "nvvideo-converter");
  nvosd = make_element ("nvdsosd", "nv-onscreendisplay");
  transform = make_element ("nvegltransform", "nvegl-transform");
  sink = make_element ("nveglglessink", "nvvideo-renderer");

  g_object_set(G_OBJECT(source), "device", "/dev/video0", NULL);

  /* Set all the necessary properties of the nvinfer element,
   * the necessary ones are : */
  g_object_set (G_OBJECT (pgie), "config-file-path", "dstest1_pgie_config.yml", NULL);

  GstCaps* caps1;
  GstCaps* caps2;
  GstCaps* caps3;
  caps1 = gst_caps_from_string("video/x-raw, width=640, height=480, format=YUY2, framerate=30/1");
  g_object_set(G_OBJECT(caps_v4l2src), "caps", caps1, NULL);

  caps2 = gst_caps_from_string("video/x-raw, format=NV12");
  g_object_set(G_OBJECT(caps_srcconv), "caps", caps2, NULL);

  caps3 = gst_caps_from_string("video/x-raw(memory:NVMM), format=NV12");
  g_object_set(G_OBJECT(caps_vidconvsrc), "caps", caps3, NULL);

  gst_caps_unref(caps1);
  gst_caps_unref(caps2);
  gst_caps_unref(caps3);
 
  //caps_uyvy = gst_caps_new_simple ("video/x-raw", "format", G_TYPE_STRING, "YUYV",
  //    "width", G_TYPE_INT, 640, "height", G_TYPE_INT,480, "framerate", GST_TYPE_FRACTION,
  //    30, 1, NULL);
  //caps_nv12_nvmm = gst_caps_new_simple ("video/x-raw", "format", G_TYPE_STRING, "NV12", NULL);
  //feature = gst_caps_features_new ("memory:NVMM", NULL);
  //gst_caps_set_features (caps_nv12_nvmm, 0, feature);
  //caps_nv12 = gst_caps_new_simple ("video/x-raw", "format", G_TYPE_STRING, "NV12", NULL);
  //gst_caps_unref(caps_uyvy);
  //gst_caps_unref(caps_nv12_nvmm);
  //gst_caps_unref(caps_nv12);
    /* Finally render the osd output */
  g_object_set (G_OBJECT (streammux), 
        "width", MUXER_OUTPUT_WIDTH, 
        "height", MUXER_OUTPUT_HEIGHT, 
        "batch-size", 1, 
        "batched-push-timeout", MUXER_BATCH_TIMEOUT_USEC, 
        "live-source", TRUE, NULL);

  /* we add a message handler */
  bus = gst_pipeline_get_bus (GST_PIPELINE (pipeline));
  bus_watch_id = gst_bus_add_watch (bus, bus_call, loop);
  gst_object_unref (bus);

  /* Set up the pipeline */
  /* we add all elements into the pipeline */
  gst_bin_add_many (GST_BIN (pipeline),
      source, caps_v4l2src, src_conv, caps_srcconv, nvconv, caps_vidconvsrc, streammux, pgie,
      nvvidconv, nvosd, transform, sink, NULL);

  gst_element_link(source, caps_v4l2src);
  gst_element_link(caps_v4l2src, src_conv);
  gst_element_link(src_conv, caps_srcconv);
  gst_element_link(caps_srcconv, nvconv);
  gst_element_link(nvconv, caps_vidconvsrc);
  
  //gst_element_link(caps_vidconvsrc, streammux);
  GstPad *sinkpad, *srcpad;
  gchar pad_name_sink[16] = "sink_0";
  gchar pad_name_src[16] = "src";

  sinkpad = gst_element_get_request_pad (streammux, pad_name_sink);
  if (!sinkpad) {
    g_printerr ("Streammux request sink pad failed. Exiting.\n");
    return -1;
  }

  srcpad = gst_element_get_static_pad (caps_vidconvsrc, pad_name_src);
  if (!srcpad) {
    g_printerr ("caps_vidconvsrc request src pad failed. Exiting.\n");
    return -1;
  }

  if (gst_pad_link (srcpad, sinkpad) != GST_PAD_LINK_OK) {
      g_printerr ("Failed to link capsfilter to stream muxer. Exiting.\n");
      return -1;
  }
  gst_object_unref(GST_OBJECT(sinkpad));
  gst_object_unref(GST_OBJECT(srcpad));

  gst_element_link(streammux, pgie);
  gst_element_link(pgie, nvvidconv);
  gst_element_link(nvvidconv, nvosd);
  gst_element_link(nvosd, transform);
  gst_element_link(transform, sink);

  //if (!gst_element_link_many (source, caps_v4l2src, src_conv, nvconv, caps_vidconvsrc, NULL)) {
  //  g_printerr ("Elements could not be linked: 1. Exiting.\n");
  //  return -1;
  //}

  //if (!gst_element_link_many (streammux, pgie, nvvidconv, nvosd, transform, sink, NULL)) {
  //    g_printerr ("Elements could not be linked: 2. Exiting.\n");
  //  return -1;
  //}



  /* Lets add probe to get informed of the meta data generated, we add probe to
   * the sink pad of the osd element, since by that time, the buffer would have
   * had got all the metadata. */
  osd_sink_pad = gst_element_get_static_pad (nvosd, "sink");
  if (!osd_sink_pad)
    g_print ("Unable to get sink pad\n");
  else
    gst_pad_add_probe (osd_sink_pad, GST_PAD_PROBE_TYPE_BUFFER,
        osd_sink_pad_buffer_probe, NULL, NULL);

  /* Set the pipeline to "playing" state */
  gst_element_set_state (pipeline, GST_STATE_PLAYING);

  /* Wait till pipeline encounters an error or EOS */
  g_print ("Running...\n");
  g_main_loop_run (loop);

  /* Out of the main loop, clean up nicely */
  g_print ("Returned, stopping playback\n");
  gst_element_set_state (pipeline, GST_STATE_NULL);
  g_print ("Deleting pipeline\n");
  gst_object_unref (GST_OBJECT (pipeline));
  g_source_remove (bus_watch_id);
  g_main_loop_unref (loop);
  return 0;
}
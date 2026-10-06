# How Machines Learned to See — narration script

A two-minute documentary on computer vision: from MIT's 1966 Summer Vision
Project to the neural networks that now watch every frame.

Running time: **2:01** · Voice: synthetic (Kokoro TTS, voice `af_heart`)

| Time | Picture | Narration |
|---|---|---|
| 0:00 | **Cold open.** Inside one security feed in a store aisle; the camera pulls back to reveal a wall of 16 live feeds. The wall drains of colour; a terminal line reads `OBJECTS UNDERSTOOD: 0`. | There are now billions of cameras on Earth. They watch our streets, our shops, our workplaces. But for most of history, not one of them understood a single thing it saw. |
| 0:12 | **Title.** Autofocus brackets close on the title, which gets its own detector label: `TITLE 0.99`. | — |
| 0:16 | **1966.** A typewritten MIT memo heading (*The Summer Vision Project*); three month boxes get a "ONE SUMMER" stamp; a year counter runs 1966 → 2012 (+46 years). | In the summer of 1966, researchers at MIT set out to teach a computer to pick out objects in a picture. They gave themselves one summer. It would take nearly half a century. |
| 0:29 | **Pixels.** Two faces, a cut to a street, then a continuous zoom into one eye until the image becomes a grid of real RGB values. The grid then splits into its red, green and blue layers. | Because a computer doesn't see a face, or a street. It sees a grid of numbers. Millions of them. Each one, just a measure of red, green, or blue light. |
| 0:40 | **Hand-written rules.** A `rules.py` panel types itself out. Real Canny edges and corner points are drawn over the footage, then a hand-made head-and-body template matches (`PERSON? YES`). Then the light drops, the camera tilts and a shadow sweeps across, and the same rules fail (`RuleError`). | For decades, engineers tried to write the rules by hand. Find the edges. Find the corners. Describe exactly what a person looks like. But change the lighting, the angle, or the shadows, and the rules fall apart. |
| 0:54 | **Learning.** RULES flips to EXAMPLES. Labelled crops taken from the footage slide into a neural network. Activations ripple through its layers and the output settles on the right answer while a counter of examples seen climbs past a million. | So researchers flipped the problem. Instead of writing the rules, let the machine learn them, from examples. Layers of artificial neurons, tuning themselves across millions of images. |
| 1:06 | **ImageNet.** A mosaic of labelled images fills in as the counter reaches 14,197,122. That gives way to a bar chart of each year's winning ImageNet error: 28.2% → 25.8% → **15.3% (AlexNet)** → 11.7% → 6.7% → **3.6% (ResNet)**, which drops below the 5.1% human line. | In 2009, a project called ImageNet gathered more than fourteen million labeled photos. In 2012, a neural network called AlexNet slashed the error rate in the ImageNet challenge. Three years later, machines were making fewer mistakes on that test than a trained human. |
| 1:26 | **Today.** Live detections on real footage: apple, car, bottles. In a parking lot a scan line sweeps the frame, and the person, car and bicycle boxes each light up as the narrator names them. Then a shopper counter in a store aisle, and a warehouse worker stepping into a restricted floor zone (`WORKER IN DANGER ZONE`). | Today, that ability is everywhere. Faster than you can blink, a machine scans each frame and draws a box. Person. Car. Bicycle. It counts shoppers in a store, and warns when a worker steps into a danger zone. |
| 1:40 | **Watch.** A cold, desaturated classroom with every face boxed. A face-landmark mesh feeds an "identity search" panel that ends in a match with the name redacted. Then the opening wall of feeds returns, now with every object boxed. The footage fades out until only the boxes are left glowing in the dark. | But a machine that can see can also watch. The same technology that finds a face in a crowd can be used to recognize whose face it is. Machines have learned to see. The question now is what we let them look at. |
| 1:55 | **End card** and credits. | — |

## What's real

- **Footage:** real video from the
  [Intel IoT DevKit sample-videos](https://github.com/intel-iot-devkit/sample-videos)
  collection (CC BY 4.0).
- **Detections:** every box, face landmark and label on the footage comes from
  real detectors run on those frames. Objects use YOLOX-S and faces use YuNet,
  both from the OpenCV Model Zoo. Edges and corners are real Canny and
  Shi-Tomasi output. The pixel values in the zoom are the frame's actual RGB
  values. The training-example crops are cut from the footage using those
  detections.
- **Dramatised:** the "identity search" panel is an illustration. Nobody is
  identified, and the name field is redacted on purpose. The network diagram
  and its "examples seen" counter are a schematic of how training works, not a
  real training run. The mosaic tiles are crops from the footage standing in
  for a large labelled dataset; they are not ImageNet images.

## Fact sources

- MIT AI Group, *The Summer Vision Project*, Vision Memo No. 100
  (S. Papert, July 1966).
- ImageNet: 14,197,122 images in 21,841 categories (image-net.org; Deng et al.,
  CVPR 2009).
- Top-5 error of each year's ILSVRC classification winner: 2010 NEC-UIUC
  28.2%; 2011 XRCE 25.8%; 2012 SuperVision/AlexNet 15.3%; 2013 Clarifai 11.7%;
  2014 GoogLeNet 6.7%; 2015 ResNet (MSRA) 3.57% (Russakovsky et al., IJCV
  2015; He et al., 2015).
- Human top-5 error of about 5.1%: A. Karpathy, "What I learned from competing
  against a ConvNet on ImageNet" (2014).

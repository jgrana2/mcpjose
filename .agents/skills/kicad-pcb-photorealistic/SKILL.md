---
name: kicad-pcb-photorealistic
description: Transform KiCad PCB 3D renders into photorealistic marketing-ready images while preserving technical details and perfect perspective alignment.
license: Complete terms in LICENSE.txt
---

# KiCad PCB 3D Render to Photorealistic Converter

Transform KiCad PCB 3D renders into photorealistic marketing-ready images while preserving all technical details and maintaining perfect perspective alignment for side-by-side comparison.

## Use Cases

- **Pitch Decks**: Impress investors with professional product photography before manufacturing
- **Marketing Materials**: Website hero images, brochures, social media content
- **Proof of Concepts**: Validate design aesthetics before fabrication
- **Engineering Reviews**: Visualize final product appearance for stakeholder approval
- **Documentation**: Technical manuals and assembly guides
- **Crowdfunding Campaigns**: Kickstarter/Indiegogo campaign imagery

## Input Requirements

### Source Image Specifications
- **Format**: PNG, JPG, or TIFF
- **Resolution**: Minimum 1920x1080, ideally 4K (3840x2160) or higher
- **Background**: Solid color (neutral gray #808080 recommended) or transparent
- **Angle**: Any isometric, top-down, or perspective view
- **Quality**: High-quality KiCad 3D render with ray tracing enabled
- **Components**: All 3D models properly aligned and scaled

### Required Input Data
- KiCad PCB 3D render image
- Board dimensions (length x width x thickness in mm)
- Layer stackup information (if available)
- List of major components with package types
- Target use case (marketing, technical, pitch deck)

## Output Specifications

### Technical Requirements
- **Format**: PNG (lossless) or high-quality JPG (95%+ quality)
- **Resolution**: Match or exceed input resolution
- **Color Space**: sRGB for web, Adobe RGB for print
- **Perspective**: Identical to input (pixel-perfect alignment possible)
- **Aspect Ratio**: 1:1 with input image

### Quality Standards
- Photorealistic materials and lighting
- Accurate component geometry preservation
- Realistic solder joint details
- Surface imperfections and manufacturing artifacts
- Proper depth of field (if applicable)
- Consistent color temperature

## Detailed Requirements

### 1. Perspective and Geometry Preservation (CRITICAL)

**MUST MAINTAIN:**
- Exact camera angle and field of view
- Board orientation and tilt
- Component positions (pixel-perfect alignment)
- Relative scaling of all elements
- Vanishing points for perspective accuracy

**Verification Method:**
- Output should overlay perfectly on input with 50% opacity
- No component position shifts > 2 pixels at 4K resolution
- No perspective distortion changes

### 2. PCB Material Realism

#### PCB Substrate (FR4)
- **Color**: Natural tan/beige to dark brown depending on manufacturer
- **Texture**: Subtle fiber glass weave pattern visible at edges
- **Translucency**: Slight light transmission at thin edge sections
- **Surface**: Matte finish with microscopic surface roughness
- **Edge Quality**: Clean cut edges with minimal burring

#### Solder Mask
- **Colors**: 
  - Green (most common): Deep forest green to teal
  - Blue: Rich royal blue
  - Black: Deep matte black
  - Red: Vibrant red
  - White: Clean bright white
  - Custom: Match exact Pantone/RAL color codes
- **Finish**: 
  - Matte: Non-reflective, soft appearance
  - Glossy: Subtle sheen, light reflections
- **Thickness**: 10-25μm visible at component edges
- **Coverage**: Complete coverage with slight relief around pads

#### Copper Layers
- **Color**: Warm copper tones (fresh) to oxidized brown (aged)
- **Finish Types**:
  - HASL (Hot Air Solder Leveling): Slightly wavy, solder-coated
  - ENIG (Electroless Nickel Immersion Gold): Flat, golden
  - OSP (Organic Solderability Preservative): Copper-colored, organic coating
  - Immersion Silver: Bright silver-white
  - Immersion Tin: Matte silver-gray
- **Traces**: Sharp edges, correct width, visible copper thickness
- **Pads**: Proper annular rings, via tenting visible

#### Silk Screen (Legend)
- **Color**: Typically white (on dark masks) or black (on light masks)
- **Font**: KiCad's default vector fonts preserved
- **Texture**: Slightly raised, matte ink texture
- **Alignment**: Perfect registration with pads and holes
- **Clarity**: Sharp text and symbols, no bleeding
- **Thickness**: ~20μm ink height

### 3. Component Realism

#### Integrated Circuits (ICs)
**QFP (Quad Flat Package):**
- Body: Black or natural epoxy compound
- Surface: Matte with subtle mold marks
- Leads: Tin or gold-plated copper, gull-wing shape
- Lead finish: Proper solder fillets at board interface
- Markings: Laser-etched or ink-printed part numbers
- Dimensions: Accurate body size, lead pitch, standoff height

**QFN/DFN (Quad Flat No-Lead):**
- Body: Similar to QFP but no visible leads
- Pads: Exposed thermal pad underneath
- Terminal pads: Silver or tin finish on package bottom
- Height: Low profile, minimal standoff

**BGA (Ball Grid Array):**
- Body: Dark substrate
- Balls: Solder spheres with proper size (0.3-0.76mm typical)
- Ball finish: Shiny solder with flux residue
- Alignment: Balls aligned with PCB pads

**SOIC/SOP (Small Outline):**
- Body: Black or natural epoxy
- Leads: Gull-wing leads with proper pitch (1.27mm SOIC, 0.65mm TSSOP)
- Lead count: Accurate number of pins
- Markings: Pin 1 indicator, part numbers

#### Passive Components

**Resistors:**
- **SMD (0402, 0603, 0805, 1206, etc.):**
  - Body: Black or blue substrate
  - Terminations: Silver or tin-plated end caps
  - Markings: Value codes (if visible at resolution)
  - Dimensions: Exact package proportions
  
- **Through-hole:**
  - Body: Beige/cream ceramic or film
  - Bands: Accurate color coding
  - Leads: Axial, bent at correct angles
  - Solder: Fillet on both sides of board

**Capacitors:**
- **Ceramic (MLCC):**
  - Body: Tan/brown ceramic
  - Terminations: Nickel barrier with tin or silver finish
  - No markings (usually) or subtle part numbers
  
- **Electrolytic (Aluminum):**
  - Can: Cylindrical aluminum with vent scores
  - Sleeve: Colored plastic (black, blue, gold)
  - Markings: Value, voltage rating, polarity stripe
  - Height: Correct can height for voltage rating
  
- **Tantalum:**
  - Body: Molded epoxy, various colors
  - Polarity: Beveled edge or stripe marking
  - Terminations: Underneath pads

**Inductors:**
- **SMD:**
  - Body: Black or natural ferrite
  - Markings: Value codes
  - Shielding: Some have metallic shields
  
- **Through-hole:**
  - Drums: Ferrite or iron powder cores
  - Wire: Copper windings visible
  - Coating: Protective varnish or epoxy

#### Connectors

**Headers (Pin Headers):**
- Housing: Black or white plastic (PBT, PA66)
- Pins: Gold or tin-plated brass/square wire
- Pin shape: Square or round as appropriate
- Height: Correct above-board dimension
- Markings: Pin numbers molded into housing

**USB Connectors:**
- Shell: Stainless steel, nickel-plated
- Housing: Black or blue plastic
- Pins: Gold-plated contacts visible
- Shield: Proper ground connection
- Dimensions: Micro, Mini, Type-A, Type-C as specified

**Board-to-Board:**
- Housing: High-temp plastic (LCP, PPS)
- Contacts: Phosphor bronze, gold-plated
- Latches: Locking mechanisms visible
- Keying: Polarization features

#### LEDs
- **SMD:**
  - Package: Clear or diffused epoxy
  - Color: Matches emission color when off (subtle)
  - Cathode mark: Visual polarity indicator
  - Lens: Flat or domed top
  
- **Through-hole:**
  - Lens: Colored or clear epoxy
  - Leads: Different lengths (cathode shorter)
  - Body: Standard 3mm or 5mm packages

#### Crystals/Oscillators
- **HC-49/SMD variants:**
  - Metal can: Shiny or matte finish
  - Sealing: Seam around can edge
  - Markings: Frequency printed on top
  - Height: Correct profile
  
- **Ceramic resonators:**
  - Body: Dark blue or black
  - Terminals: Silver pads
  - Three-terminal or two-terminal as appropriate

#### Switches and Buttons
- **Tactile switches:**
  - Body: Black or natural plastic
  - Actuator: Color-matched or contrasting
  - Height: 3.5mm, 4.3mm, 5.0mm variants
  - Terminals: Through-hole or SMD
  
- **DIP switches:**
  - Housing: Blue, red, or black
  - Switches: White or colored actuators
  - Numbers: Position indicators

### 4. Solder and Assembly Details

#### Solder Joints
**SMD Components:**
- **Proper Fillet Shape:**
  - Concave fillet at component termination
  - Wetting angle 15-45 degrees
  - Smooth, shiny surface (lead-free: matte)
  - No icicles or spikes
  
**Through-hole Components:**
- **Top side:**
  - Solder wicking into plated through-hole
  - Minimal solder above surface
  
- **Bottom side:**
  - Concave fillet surrounding lead
  - Lead trimmed to appropriate length (0.5-1.5mm)
  - Lead wire end visible (copper color)

#### Solder Defects (Realistic Imperfections)
- **Minor bridging:** Occasional hair bridges on fine-pitch ICs (if realistic)
- **Flux residue:** Slight amber tint around joints, especially on BGAs
- **Cold joints:** Occasional grainy appearance (very subtle)
- **Tombstoning:** Rare, small passives slightly lifted (if adding defects)
- **Solder balls:** Tiny spheres near QFPs (occasional)
- **Voiding:** BGA balls with slight internal voids (translucent view)

#### Manufacturing Marks
- **Test points:** Small round or square exposed copper
- **Debug headers:** Unpopulated pads with flux residue
- **Component orientation dots:** Silk screen indicators
- **Version/revision marks:** PCB version numbers
- **Date codes:** YYWW format (Year Week)
- **UL/CE marks:** Regulatory markings in silk

### 5. Surface Finish and Texture

#### Board Surface
- **Subtle scratches:** Light handling marks from assembly
- **Fingerprints:** Occasional smudges (realistic but not excessive)
- **Dust particles:** Microscopic dust (marketing: clean; realistic: slight)
- **Reflections:** Soft, diffused reflections of environment
- **Shadow casting:** Components cast subtle shadows on board

#### Component Surfaces
- **IC tops:** Subtle parting lines from molding
- **Connector plastics:** Slight sink marks or flow lines
- **Metal shields:** Fine brush marks or grain
- **Crystals:** Polished metal surfaces

### 6. Lighting and Camera

#### Lighting Setup (DSLR Simulation)
- **Key light:** 45-degree angle, softbox or diffused
- **Fill light:** -2 to -3 stops from key, opposite side
- **Rim light:** Subtle highlight on component edges
- **Ambient:** Soft, natural room light
- **Color temperature:** 5600K (daylight) or 3200K (warm)
- **Reflections:** Soft environmental reflections on glossy surfaces

#### Camera Characteristics
- **Sensor:** Full-frame DSLR simulation
- **Lens:** 50mm-100mm macro lens equivalent
- **Aperture:** f/8-f/11 for good depth of field (or f/2.8 for shallow)
- **ISO:** 100-400 (clean, low noise)
- **Focus:** Sharp focus on board surface, slight falloff at edges acceptable
- **Distortion:** Minimal barrel or pincushion (<1%)
- **Chromatic aberration:** Minimal, realistic lens CA
- **Vignetting:** Subtle darkening at corners (optional)

### 7. Environmental Context (Optional)

#### Background Options
- **Pure white:** #FFFFFF for product photography
- **Pure black:** #000000 for dramatic presentation
- **Gradient:** Subtle gray gradient
- **Environmental:** Soft bokeh office/lab background (very blurred)
- **Surface:** Wood desk, anti-static mat, or metal workbench

#### Supporting Elements (if requested)
- **Scale reference:** Ruler, coin, or known object
- **Tools:** Soldering iron, tweezers (soft focus background)
- **Hands:** Wearing ESD gloves (if showing scale)
- **Packaging:** ESD bag or box in background

## Workflow

### Step 1: Analyze Input
1. Examine the KiCad 3D render carefully
2. Identify all component types and packages
3. Note the viewing angle and perspective
4. Determine board characteristics (color, finish)
5. Assess image quality and resolution

### Step 2: Gather Information
1. Request board stackup and materials if available
2. Identify any custom or unusual components
3. Determine target aesthetic (clean marketing vs. realistic engineering)
4. Confirm color accuracy requirements

### Step 3: Generate Photorealistic Version

**Important:** When using `mcpjose_generate_image`, you MUST provide the input KiCad render as the `image_path` parameter. This ensures the AI maintains exact perspective alignment and component positioning from the original render.

**Base Prompt Structure:**
```
Transform this KiCad PCB 3D render into a photorealistic photograph. 

CRITICAL - PRESERVE EXACTLY:
- Camera angle and perspective (maintain identical viewpoint)
- Component positions and orientations
- Board dimensions and proportions
- All traces, pads, and silk screen details
- Component package types and sizes

PCB SPECIFICATIONS:
- Board size: [X]mm x [Y]mm, [Z]mm thickness
- Solder mask color: [COLOR] with [MATTE/GLOSSY] finish
- Copper finish: [HASL/ENIG/OSP/etc.]
- Silk screen color: [COLOR]

COMPONENTS TO ACCURATELY RENDER:
[List major ICs with package types]
[List connectors with specific types]
[List passives with package sizes]

PHOTOREALISTIC DETAILS TO ADD:
- Realistic PCB substrate texture (FR4 fiberglass weave at edges)
- Accurate solder mask appearance with proper thickness
- Photorealistic copper with [FINISH TYPE] finish
- Component-specific materials:
  * ICs: Molded epoxy bodies with laser-etched markings
  * Passives: Correct body colors and termination finishes
  * Connectors: Proper plastic housings and metal contacts
- Solder joints with proper fillets and wetting
- Manufacturing imperfections (subtle flux residue, minor scratches)
- Proper surface finishes (matte plastics, metallic reflections)

CAMERA SETUP:
- DSLR simulation with [LENS]mm macro lens
- Aperture f/[NUMBER] for [DEPTH OF FIELD DESCRIPTION]
- Lighting: Soft key light at 45°, fill light, subtle rim light
- Color temperature: [TEMP]K
- [HIGH/MODERATE/NO] depth of field

OUTPUT REQUIREMENTS:
- Pixel-perfect perspective alignment with input
- Photorealistic materials and lighting
- [CLEAN MARKETING / REALISTIC ENGINEERING] aesthetic
- High resolution matching input
- Transparent/solid [COLOR] background
```

### Step 4: Quality Verification

**Technical Checks:**
- [ ] Overlay test: Output aligns with input at 50% opacity
- [ ] Component count: All components present and accounted for
- [ ] Package accuracy: Each component matches real-world counterpart
- [ ] Color accuracy: PCB colors match specification
- [ ] Perspective: No distortion or angle changes

**Realism Checks:**
- [ ] Materials: PCB looks like real FR4, not plastic
- [ ] Solder: Joints look metallic, not painted
- [ ] Components: ICs have realistic epoxy texture
- [ ] Lighting: Natural shadows and reflections
- [ ] Imperfections: Appropriate level of manufacturing realism

**Comparison Setup:**
- Create side-by-side comparison image
- Input on left, output on right
- Add subtle separator line or background distinction
- Optional: 50% opacity overlay animation

## Advanced Techniques

### 1. Component-Specific Detailing

**For High-Profile Components (MCUs, FPGAs):**
- Research actual chip markings and logos
- Verify package dimensions (thermal pads, exposed metal)
- Add realistic heat spreader details if applicable

**For Connectors:**
- Identify exact manufacturer part numbers if possible
- Match connector color (many have specific brand colors)
- Include locking mechanisms and polarization keys

**For Custom Components:**
- Request 3D models or detailed drawings
- Verify keepout areas and height constraints
- Add custom silk screen or labels

### 2. Layer Stackup Visualization (Optional)

For educational or technical marketing:
- Create cutaway view showing internal layers
- Show copper thickness, prepreg, core materials
- Illustrate via plating and aspect ratios
- Maintain photorealistic style

### 3. Assembly State Variations

**Bare Board:**
- No components populated
- Show solder paste on pads (optional)
- Highlight PCB fabrication quality

**Partially Assembled:**
- Key components only (processor, memory)
- Show assembly process stages
- Useful for manufacturing documentation

**Fully Assembled:**
- All components populated
- Include shields, heatsinks, connectors
- Final product appearance

**With Enclosure:**
- Show PCB installed in case
- Visible through openings or transparent cover
- Final product integration

### 4. Artistic Enhancements

**Dramatic Lighting:**
- Strong directional light with deep shadows
- Rim lighting to highlight edges
- Color gels for creative effect
- Maintains photorealism while adding style

**Exploded View:**
- Components slightly separated from board
- Shows assembly order and relationships
- Maintains photorealism
- Adds technical illustration value

**X-Ray Style:**
- Semi-transparent view showing traces
- Useful for technical documentation
- Shows internal layer routing
- Maintains 3D perspective

## Common Pitfalls and Solutions

### Problem: Perspective Mismatch
**Symptom:** Components don't align when overlaying images
**Solution:** 
- Use image editing software to verify alignment
- Adjust generation parameters for exact FOV match
- Consider using input image as depth/position reference

### Problem: Plastic-Looking PCB
**Symptom:** Board looks like molded plastic instead of FR4
**Solution:**
- Emphasize fiberglass weave texture in prompt
- Add edge translucency where light passes through
- Reference real PCB photos for material appearance

### Problem: Wrong Component Sizes
**Symptom:** Components appear disproportionate
**Solution:**
- Provide specific package dimensions in prompt
- Use reference measurements (ruler, known objects)
- Verify against datasheet dimensions

### Problem: Unrealistic Solder
**Symptom:** Solder looks painted or uniform
**Solution:**
- Request specific solder joint shapes
- Reference IPC-A-610 standards for acceptable joints
- Add variation: different joint sizes, slight imperfections

### Problem: Too Clean/Perfect
**Symptom:** Looks CGI, not photographed
**Solution:**
- Add subtle dust, fingerprints, handling marks
- Include minor assembly defects
- Vary component alignment slightly (within tolerance)
- Add environmental reflections

## Output Formats

### For Marketing
- **Resolution**: 4K or 8K
- **Format**: PNG (web), TIFF (print)
- **Background**: White or transparent
- **Style**: Clean, professional, minimal defects
- **Aspect Ratio**: 16:9, 1:1, or 4:5 for social media

### For Engineering
- **Resolution**: Match input
- **Format**: PNG
- **Background**: Neutral gray
- **Style**: Realistic with manufacturing details
- **Annotations**: Optional callouts for key components

### For Documentation
- **Resolution**: 1920x1080 minimum
- **Format**: PNG
- **Background**: White
- **Style**: Clear, well-lit, all components visible
- **Variants**: Multiple angles if needed

## Tools and Resources

### Recommended Generation Tools
- **Primary**: `mcpjose_generate_image` with Gemini
  - **Important**: Pass the input KiCad render image as the `image_path` parameter to maintain exact perspective alignment
  - Set `output_path` to save the photorealistic result
- **Alternative**: Image-to-image diffusion models
- **Post-processing**: GIMP, Photoshop for alignment verification

### Reference Resources
- **IPC Standards**: IPC-A-610 (Acceptability of Electronic Assemblies)
- **Component Datasheets**: Manufacturer websites for accurate dimensions
- **Real PCB Photos**: Macro photography of actual assembled boards
- **KiCad 3D Viewer**: Export high-quality renders with ray tracing

### Color References
- **Solder Mask Green**: Pantone 3415C or similar
- **Solder Mask Blue**: Pantone 293C
- **Solder Mask Black**: Neutral black
- **Copper**: Metallic copper with oxidation variations
- **Gold (ENIG)**: Pale yellow metallic
- **Silver**: Bright white metallic

## Examples

### Example 1: IoT Sensor Board
**Input**: KiCad 3D render of ESP32-based sensor board
**Specifications**:
- Board: 50mm x 30mm, 1.6mm thickness
- Solder mask: Green, matte
- Finish: ENIG
- Components: ESP32-WROOM, sensors, USB-C, passives

**Output**: Photorealistic image with:
- Realistic ESP32 module with shield can
- Gold-plated USB-C connector
- Tiny 0402 passives properly scaled
- ENIG finish on copper areas
- Soft studio lighting with subtle reflections

### Example 2: Motor Controller
**Input**: High-power motor driver PCB
**Specifications**:
- Board: 100mm x 80mm, 2.0mm thickness
- Solder mask: Blue, glossy
- Finish: HASL
- Components: Large MOSFETs, heatsinks, terminal blocks

**Output**: Photorealistic image with:
- TO-220 packages with heatsinks
- Thick copper traces with HASL finish
- Large electrolytic capacitors
- Heavy-duty terminal blocks
- Industrial lighting with dramatic shadows

### Example 3: RF Module
**Input**: Wireless communication module
**Specifications**:
- Board: 25mm x 20mm, 0.8mm thickness
- Solder mask: Black, matte
- Finish: Immersion silver
- Components: RF IC, crystal, antenna, matching network

**Output**: Photorealistic image with:
- RF shield can with proper finish
- Tiny crystal with visible markings
- PCB antenna with precise trace geometry
- Immersion silver finish on pads
- Clinical lighting for inspection aesthetic

## Quality Checklist

Before delivering final image, verify:

### Technical Accuracy
- [ ] All components present and correctly positioned
- [ ] Component packages match real-world counterparts
- [ ] PCB colors and finishes accurate
- [ ] Trace widths and spacing preserved
- [ ] Silk screen text legible and aligned
- [ ] Pad sizes and shapes correct
- [ ] Perspective matches input exactly

### Photorealism
- [ ] Materials look real (not plastic or CGI)
- [ ] Lighting appears natural with proper shadows
- [ ] Reflections appropriate for surface types
- [ ] Solder joints look metallic and properly formed
- [ ] Component textures realistic (molded plastic, metal, ceramic)
- [ ] Surface imperfections add realism without distraction

### Professional Quality
- [ ] Image sharpness and clarity
- [ ] Color balance and temperature
- [ ] No artifacts, noise, or compression issues
- [ ] Proper exposure (no clipped highlights or shadows)
- [ ] Clean edges and professional presentation

## Tips for Best Results

1. **Start with High-Quality Input**: The better the KiCad render, the better the photorealistic result
2. **Provide Detailed Specifications**: More context leads to more accurate results
3. **Reference Real Photos**: Compare against actual PCB photos for realism
4. **Iterate if Needed**: First attempt may need adjustments for perfection
5. **Verify Alignment**: Always check that output aligns with input
6. **Consider the Use Case**: Adjust realism level based on final application
7. **Maintain Consistency**: Use same lighting/camera setup for product families
8. **Document Settings**: Save successful prompts for future projects

## Troubleshooting

**Issue**: Components look "painted on" rather than 3D
**Fix**: Emphasize "physical 3D geometry", "casting shadows", "real depth"

**Issue**: Board looks too clean/artificial
**Fix**: Add "manufacturing imperfections", "flux residue", "microscopic dust"

**Issue**: Wrong component colors
**Fix**: Specify exact colors: "black epoxy IC bodies", "tan ceramic capacitors"

**Issue**: Solder mask looks flat
**Fix**: Request "solder mask thickness visible at component edges", "subtle texture"

**Issue**: Perspective doesn't match
**Fix**: Explicitly state "maintain exact same camera angle and field of view"

## Conclusion

This skill enables transformation of technical PCB 3D renders into compelling photorealistic images suitable for any professional application. By maintaining strict perspective alignment while adding realistic materials, lighting, and manufacturing details, the output can be used confidently in pitch decks, marketing materials, and engineering documentation.

The key to success is attention to detail: accurate component representations, realistic materials, proper lighting, and manufacturing authenticity. When executed correctly, the photorealistic version should be virtually indistinguishable from a high-quality photograph of the actual assembled PCB.

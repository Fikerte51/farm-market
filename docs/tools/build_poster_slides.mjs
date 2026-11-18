/** Build one editable poster slide from the PDF layout and Chen source.
 * Run this callback through Artifact Session with export_poster_objects.py data.
 * Text, section boxes, process arrows and every ER primitive stay native.
 * Decorative icons are individually cropped picture objects.
 */
import { readFile } from 'node:fs/promises';
export async function build({presentation,input}) {
 const artwork=new Uint8Array(await readFile(input.background));
 const slide=presentation.slides.getItem(0);
 slide.size={width:1456,height:1088};slide.background.fill='#fffbee';
 function rect(name,x,y,w,h,fill='#fffbee',stroke='#578564',radius=14){
  return slide.shapes.add({name,geometry:radius?'roundRect':'rect',position:{left:x,top:y,width:w,height:h},fill,
   line:{fill:stroke,width:1},borderRadius:radius});
 }
 rect('Title background',15,14,1425,194,'#004b2c','#004b2c',24);
 rect('Footer background',15,1048,1425,33,'#004b2c','#004b2c',15);
 for(const [name,x,y,w,h,hh,color] of [
  ['Overview',21,224,414,171,43],['Roles',21,407,414,244,43],['Process',21,661,414,258,41],
  ['Database',451,224,516,503,59],['Technology',451,736,516,183,48],
  ['Rules',983,224,452,299,45],['Features',983,536,452,227,46,'#fb7b18'],
  ['Advanced',983,776,452,143,43],['Testing',21,931,835,112,34]]) {
   rect(name+' section',x,y,w,h);rect(name+' heading',x,y,w,hh,color||'#004b2c',color||'#004b2c',13);
 }
 for(const [name,x,w,col] of [['Farmer',29,128,'#91af64'],['Buyer',164,131,'#f78b3c'],['Administrator',302,126,'#91af64']])
  rect(name+' role panel',x,460,w,184,'#fffbee',col,12);
 rect('Advanced details panel',997,831,422,76,'#fffbee','#578564',12);
 // Original artwork stays separate and movable. Crop fractions are native image properties.
 function art(name,x,y,w,h) {
  slide.images.add({blob:artwork,contentType:'image/png',alt:name,fit:'cover',position:{left:x,top:y,width:w,height:h},
   crop:{left:x/1456,top:y/1088,right:1-(x+w)/1456,bottom:1-(y+h)/1088}});
 }
 for(const a of [
  ['Vegetable crate',53,29,164,165],['Tomato',1268,83,152,116],
  ['Farmer icon',58,468,71,65],['Buyer basket',195,469,67,64],['Admin shield',333,468,65,65],
  ['Farm',40,711,61,54],['Crop',141,711,59,54],['Harvest',240,711,59,54],['Stock tractor',338,711,61,54],
  ['Request',94,820,65,59],['Allocation',218,820,65,59],['Delivery',345,820,66,59],
  ['Python code icon',470,798,65,57],['Database icon',571,796,66,60],['GUI icon',678,798,63,57],
  ['LangChain icon',779,797,68,59],['Image storage icon',883,798,63,59],
  ['Search monitor',994,631,104,82],['Farm delivery landscape',860,922,576,122]]) art(...a);
 function line(name,x1,y1,x2,y2,width=1.3,color='#004b2c'){
  const l=Math.min(x1,x2),t=Math.min(y1,y2),w=Math.max(Math.abs(x2-x1),.01),h=Math.max(Math.abs(y2-y1),.01);
  slide.shapes.add({name,geometry:'custom',position:{left:l,top:t,width:w,height:h},fill:'none',line:{fill:color,width},
   customPaths:[{width:w,height:h,commands:[{moveTo:{x:x1-l,y:y1-t}},{lineTo:{x:x2-l,y:y2-t}}]}]});
 }
 line('Business rule divider',1198,291,1198,506);
 for(const x of [550,651,767,869])line('Technology divider '+x,x,795,x,908,1,'#7b977b');
 for(const [x,y] of [[106,739],[207,739],[307,739],[161,854],[306,854]])
  slide.shapes.add({name:'Process arrow',geometry:'rightArrow',position:{left:x,top:y,width:27,height:12},fill:'#004b2c',line:{fill:'none',width:0}});
 line('Farm to request vertical',54,799,54,856,2);line('Farm to request horizontal',54,856,80,856,2);
 slide.shapes.add({name:'Request arrowhead',geometry:'rightArrow',position:{left:74,top:850,width:14,height:12},fill:'#004b2c',line:{fill:'none',width:0}});
 for(const [x,y] of [[999,296],[1212,296],[999,349],[1212,349],[999,402],[1212,402],[999,455],[1212,455],
  [56,974],[56,1008],[432,974],[432,1008]]) {
  slide.images.add({blob:artwork,contentType:'image/png',alt:'Check mark',fit:'cover',position:{left:x,top:y,width:25,height:25},
   crop:{left:995/1456,top:293/1088,right:1-1021/1456,bottom:1-319/1088}});
 }
 for(const y of [607,641,671,703,731])
  slide.images.add({blob:artwork,contentType:'image/png',alt:'Feature bullet',fit:'cover',position:{left:1118,top:y,width:16,height:16},
   crop:{left:1117/1456,top:606/1088,right:1-1133/1456,bottom:1-622/1088}});
 // Recreate the ER with individual editable paths, entity boxes, ovals and diamonds.
 const bounds=input.bounds,scale=Math.min(494/bounds.width,259/bounds.height),dx=462+(494-bounds.width*scale)/2,dy=433+(259-bounds.height*scale)/2;
 for(const e of input.edges) {
  const ps=e.points.map(([x,y])=>[dx+x*scale,dy+y*scale]);
  for(let i=1;i<ps.length;i++)line('ER '+e.id+' segment '+i,...ps[i-1],...ps[i],.65,'#102d1c');
 }
 for(const v of input.vertices) {
  const b=v.box,pos={left:dx+b.x*scale,top:dy+b.y*scale,width:b.width*scale,height:b.height*scale};
  const shape=slide.shapes.add({name:'ER '+v.id,geometry:v.kind==='label'?'textbox':v.kind==='ellipse'?'ellipse':v.kind==='diamond'?'diamond':'rect',
   position:pos,fill:v.kind==='rect'?'#eef5f0':'#ffffff',line:{fill:v.kind==='label'?'none':'#102d1c',width:v.kind==='label'?0:.6}});
  shape.text=v.text;shape.text.style={typeface:'Arial',fontSize:v.fs*scale,bold:true,color:'#071a0e',
   alignment:'center',verticalAlignment:'middle',insets:0,wrap:'none',autoFit:'shrinkText',...(v.key?{underline:'sng'}:{})};
 }
 // Poster copy remains independent of all section backgrounds and illustrations.
 for(const [i,t] of input.texts.entries()) {
  const sh=slide.shapes.add({name:'Poster text '+i+' '+t.text.slice(0,45),geometry:'textbox',
   position:{left:t.x,top:t.y,width:t.w,height:t.h},fill:'none',line:{fill:'none',width:0}});
  sh.text=t.text;sh.text.style={typeface:'Arial Narrow',fontSize:t.fs,bold:t.bold,color:t.color,
   alignment:t.align===1?'center':'left',verticalAlignment:'top',insets:0,lineSpacing:1.13,autoFit:'shrinkText',wrap:'square'};
 }
 slide.speakerNotes.text='One editable poster slide. Text and section boxes are native objects. The conceptual ER has individually editable entity boxes, relationship diamonds, attribute ovals, labels and line segments. Decorative farm illustrations and icons remain separate cropped picture objects. Project facts, team names, Lab B1 and test counts come from the Farm & Market project sources.';

 return {nativeShapes:slide.shapes.items.length,pictures:slide.images.items.length};
}
